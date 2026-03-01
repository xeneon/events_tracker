"""Async ingester runner with QueueHandler for SSE log streaming."""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
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

logger = logging.getLogger(__name__)

# Serialize runs so log output doesn't interleave
_semaphore = asyncio.Semaphore(1)

# In-memory state keyed by source alias
_run_status: dict[str, dict] = {}


@dataclass
class _RunInfo:
    log_buffer: list[str] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    done: bool = False


# Run state keyed by run_id — replaces _run_queues
_run_infos: dict[str, _RunInfo] = {}


class _QueueHandler(logging.Handler):
    """Logging handler that buffers and broadcasts formatted records to all subscribers."""

    def __init__(self, run_id: str):
        super().__init__()
        self._run_id = run_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            info = _run_infos.get(self._run_id)
            if info is None:
                return
            info.log_buffer.append(msg)
            for sub in info.subscribers:
                sub.put_nowait(msg)
        except Exception:
            self.handleError(record)


def get_all_statuses() -> dict[str, dict]:
    aliases = list(SOURCE_ALIASES) + ["export"]
    return {alias: _run_status.get(alias, {"state": "idle"}) for alias in aliases}


def _reload_settings() -> None:
    """Mutate the existing settings singleton in-place from the config .env file."""
    try:
        new = Settings(_env_file=_ENV_FILE)
        for field_name in Settings.model_fields:
            setattr(config_mod.settings, field_name, getattr(new, field_name))
    except Exception:
        pass  # Keep existing settings if reload fails


@asynccontextmanager
async def _log_to_run(run_id: str):
    """Attach a run-backed log handler and signal done on exit."""
    handler = _QueueHandler(run_id)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        yield
    finally:
        root_logger.removeHandler(handler)
        info = _run_infos.get(run_id)
        if info is not None:
            info.done = True
            for sub in info.subscribers:
                sub.put_nowait(None)  # sentinel — signals stream end


async def _do_export(export_query: str | None = None) -> None:
    """Fetch rows and write to Google Sheet, logging progress."""
    from ingest.export_sheets import fetch_rows, write_to_sheet

    headers, rows = await fetch_rows(inline_query=export_query)
    logger.info(f"Fetched {len(rows)} rows from database.")
    count = await asyncio.to_thread(write_to_sheet, rows, headers)
    logger.info(f"Wrote {count} rows to Google Sheet.")


async def _run_single(alias: str, run_id: str) -> None:
    source_name = SOURCE_ALIASES[alias]
    ingester_cls = INGESTERS[source_name]

    async with _log_to_run(run_id):
        try:
            _reload_settings()
            async with async_session_maker() as session:
                result = await session.execute(
                    select(DataSource).where(DataSource.name == source_name)
                )
                source = result.scalar_one_or_none()
                if not source:
                    logger.error(f"DataSource '{source_name}' not found in database.")
                    _run_status[alias] = {"state": "error", "message": "DataSource not found"}
                    return

                ingester = ingester_cls(session, source)
                count = await ingester.run()

            _run_status[alias] = {"state": "ok", "count": count}
            logger.info(f"Done: {count} events from {source_name}.")
        except Exception as e:
            _run_status[alias] = {"state": "error", "message": repr(e)}
            logger.error(f"ERROR: {e!r}", exc_info=True)


async def _run_export(run_id: str, export_query: str | None = None) -> None:
    async with _log_to_run(run_id):
        try:
            _reload_settings()
            await _do_export(export_query=export_query)
            _run_status["export"] = {"state": "ok", "count": 0}
        except Exception as e:
            _run_status["export"] = {"state": "error", "message": str(e)}
            logger.error(f"Export failed: {e}")


async def _run_all(run_id: str) -> None:
    async with _log_to_run(run_id):
        _reload_settings()
        for alias, source_name in SOURCE_ALIASES.items():
            ingester_cls = INGESTERS[source_name]
            _run_status[alias] = {"state": "running", "run_id": run_id}
            logger.info(f"\n{'='*40}\nRunning: {alias}\n{'='*40}")

            try:
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(DataSource).where(DataSource.name == source_name)
                    )
                    source = result.scalar_one_or_none()
                    if not source:
                        logger.error(f"DataSource '{source_name}' not found.")
                        _run_status[alias] = {"state": "error", "message": "DataSource not found"}
                        continue

                    ingester = ingester_cls(session, source)
                    count = await ingester.run()

                _run_status[alias] = {"state": "ok", "count": count}
                logger.info(f"Done: {count} events from {source_name}.")
            except Exception as e:
                _run_status[alias] = {"state": "error", "message": repr(e)}
                logger.error(f"ERROR in {alias}: {e!r}", exc_info=True)

        # Export step
        logger.info(f"\n{'='*40}\nRunning: export-sheets\n{'='*40}")
        try:
            await _do_export()
            _run_status["export"] = {"state": "ok", "count": 0}
        except Exception as e:
            _run_status["export"] = {"state": "error", "message": str(e)}
            logger.error(f"Export failed: {e}")


async def _run_with_semaphore(coro) -> None:
    try:
        async with _semaphore:
            await coro
    except asyncio.CancelledError:
        coro.close()  # Prevent "coroutine never awaited" warning on shutdown
        raise


def start_run(source_alias: str | None = None, export_query: str | None = None) -> str:
    """Create a RunInfo, launch the background task, return run_id."""
    run_id = str(uuid.uuid4())
    _run_infos[run_id] = _RunInfo()
    while len(_run_infos) > 20:
        _run_infos.pop(next(iter(_run_infos)))

    if source_alias == "export":
        _run_status["export"] = {"state": "running", "run_id": run_id}
        coro = _run_export(run_id, export_query=export_query)
    elif source_alias:
        _run_status[source_alias] = {"state": "running", "run_id": run_id}
        coro = _run_single(source_alias, run_id)
    else:
        for alias in SOURCE_ALIASES:
            _run_status[alias] = {"state": "running", "run_id": run_id}
        _run_status["export"] = {"state": "running", "run_id": run_id}
        coro = _run_all(run_id)

    asyncio.create_task(_run_with_semaphore(coro))
    return run_id


async def stream_run(run_id: str) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted strings for a given run."""
    info = _run_infos.get(run_id)
    if info is None:
        yield "data: Run not found\n\n"
        return

    # Subscribe and snapshot atomically (no await between)
    sub_queue: asyncio.Queue = asyncio.Queue()
    info.subscribers.append(sub_queue)
    buffered = list(info.log_buffer)
    already_done = info.done

    try:
        # Replay buffered messages
        for msg in buffered:
            lines = msg.splitlines() if msg else [""]
            for line in lines:
                yield f"data: {line}\n"
            yield "\n"

        if already_done:
            yield "data: [DONE]\n\n"
            return

        # Stream new messages until sentinel
        while True:
            msg = await sub_queue.get()
            if msg is None:
                yield "data: [DONE]\n\n"
                break
            lines = msg.splitlines() if msg else [""]
            for line in lines:
                yield f"data: {line}\n"
            yield "\n"
    finally:
        try:
            info.subscribers.remove(sub_queue)
        except ValueError:
            pass
