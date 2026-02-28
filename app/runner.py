"""Async ingester runner with QueueHandler for SSE log streaming."""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import AsyncGenerator

import ingest.config as config_mod
from ingest.config import Settings
from ingest.__main__ import INGESTERS, SOURCE_ALIASES
from ingest.db import async_session_maker
from ingest.models import DataSource
from sqlalchemy import select

_CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/config"))
_ENV_FILE = str(_CONFIG_DIR / ".env")

# Serialize runs so log output doesn't interleave
_semaphore = asyncio.Semaphore(1)

# In-memory state keyed by source alias
_run_status: dict[str, dict] = {}
# Queues keyed by run_id
_run_queues: dict[str, asyncio.Queue] = {}


class _QueueHandler(logging.Handler):
    """Logging handler that puts formatted records into an asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)


def get_all_statuses() -> dict[str, dict]:
    return {alias: _run_status.get(alias, {"state": "idle"}) for alias in SOURCE_ALIASES}


def _reload_settings() -> None:
    """Mutate the existing settings singleton in-place from the config .env file."""
    try:
        new = Settings(_env_file=_ENV_FILE)
        for field in Settings.model_fields:
            setattr(config_mod.settings, field, getattr(new, field))
    except Exception:
        pass  # Keep existing settings if reload fails


async def _run_single(alias: str, run_id: str, queue: asyncio.Queue) -> None:
    source_name = SOURCE_ALIASES[alias]
    ingester_cls = INGESTERS[source_name]

    handler = _QueueHandler(queue)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        _reload_settings()
        async with async_session_maker() as session:
            result = await session.execute(
                select(DataSource).where(DataSource.name == source_name)
            )
            source = result.scalar_one_or_none()
            if not source:
                queue.put_nowait(f"ERROR: DataSource '{source_name}' not found in database.")
                _run_status[alias] = {"state": "error", "message": "DataSource not found"}
                return

            ingester = ingester_cls(session, source)
            count = await ingester.run()

        _run_status[alias] = {"state": "ok", "count": count}
        queue.put_nowait(f"Done: {count} events from {source_name}.")
    except Exception as e:
        _run_status[alias] = {"state": "error", "message": str(e)}
        queue.put_nowait(f"ERROR: {e}")
    finally:
        root_logger.removeHandler(handler)
        queue.put_nowait(None)  # sentinel — signals stream end


async def _run_all(run_id: str, queue: asyncio.Queue) -> None:
    from ingest.export_sheets import fetch_rows, write_to_sheet

    handler = _QueueHandler(queue)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        _reload_settings()
        for alias, source_name in SOURCE_ALIASES.items():
            ingester_cls = INGESTERS[source_name]
            _run_status[alias] = {"state": "running", "run_id": run_id}
            queue.put_nowait(f"\n{'='*40}\nRunning: {alias}\n{'='*40}")

            try:
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(DataSource).where(DataSource.name == source_name)
                    )
                    source = result.scalar_one_or_none()
                    if not source:
                        queue.put_nowait(f"ERROR: DataSource '{source_name}' not found.")
                        _run_status[alias] = {"state": "error", "message": "DataSource not found"}
                        continue

                    ingester = ingester_cls(session, source)
                    count = await ingester.run()

                _run_status[alias] = {"state": "ok", "count": count}
                queue.put_nowait(f"Done: {count} events from {source_name}.")
            except Exception as e:
                _run_status[alias] = {"state": "error", "message": str(e)}
                queue.put_nowait(f"ERROR in {alias}: {e}")

        # Export step
        queue.put_nowait(f"\n{'='*40}\nRunning: export-sheets\n{'='*40}")
        try:
            rows = await fetch_rows()
            queue.put_nowait(f"Fetched {len(rows)} rows from database.")
            count = await asyncio.to_thread(write_to_sheet, rows)
            queue.put_nowait(f"Wrote {count} rows to Google Sheet.")
        except Exception as e:
            queue.put_nowait(f"Export failed: {e}")
    finally:
        root_logger.removeHandler(handler)
        queue.put_nowait(None)  # sentinel


async def _run_with_semaphore(coro) -> None:
    try:
        async with _semaphore:
            await coro
    except asyncio.CancelledError:
        coro.close()  # Prevent "coroutine never awaited" warning on shutdown
        raise


def start_run(source_alias: str | None = None) -> str:
    """Create a queue, launch the background task, return run_id."""
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = queue

    if source_alias:
        _run_status[source_alias] = {"state": "running", "run_id": run_id}
        coro = _run_single(source_alias, run_id, queue)
    else:
        for alias in SOURCE_ALIASES:
            _run_status[alias] = {"state": "running", "run_id": run_id}
        coro = _run_all(run_id, queue)

    asyncio.create_task(_run_with_semaphore(coro))
    return run_id


async def stream_run(run_id: str) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted strings for a given run."""
    queue = _run_queues.get(run_id)
    if not queue:
        yield "data: Run not found\n\n"
        return

    while True:
        msg = await queue.get()
        if msg is None:
            yield "data: [DONE]\n\n"
            break
        # Each line of a multi-line message gets its own data: prefix
        lines = msg.splitlines() if msg else [""]
        for line in lines:
            yield f"data: {line}\n"
        yield "\n"
