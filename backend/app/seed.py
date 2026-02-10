"""Seed script for initial categories, data sources, and superuser."""

import asyncio
import uuid

from fastapi_users.password import PasswordHelper
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.category import Category
from app.models.data_source import DataSource
from app.models.user import User

CATEGORIES = [
    {"name": "Federal Holiday", "slug": "federal-holiday", "color": "#dc2626", "icon": "flag", "sort_order": 1},
    {"name": "State Holiday", "slug": "state-holiday", "color": "#ea580c", "icon": "map-pin", "sort_order": 2},
    {"name": "Observance", "slug": "observance", "color": "#2563eb", "icon": "eye", "sort_order": 3},
    {"name": "Religious", "slug": "religious", "color": "#7c3aed", "icon": "heart", "sort_order": 4},
    {"name": "Movies", "slug": "movies", "color": "#ca8a04", "icon": "film", "sort_order": 6},
    {"name": "TV Shows", "slug": "tv-shows", "color": "#16a34a", "icon": "tv", "sort_order": 7},
    {"name": "Fashion", "slug": "fashion", "color": "#db2777", "icon": "scissors", "sort_order": 8},
    {"name": "Music Releases", "slug": "music-releases", "color": "#92400e", "icon": "music", "sort_order": 9},
    {"name": "Other", "slug": "other", "color": "#6b7280", "icon": "circle", "sort_order": 99},
]

DATA_SOURCES = [
    {
        "name": "Calendarific",
        "source_type": "api",
        "base_url": "https://calendarific.com/api/v2",
        "api_key_env_var": "CALENDARIFIC_API_KEY",
        "is_active": True,
        "sync_interval": 1440,
    },
    {
        "name": "Trakt",
        "source_type": "api",
        "base_url": "https://api.trakt.tv",
        "api_key_env_var": "TRAKT_CLIENT_ID",
        "is_active": True,
        "sync_interval": 1440,
    },
    {
        "name": "Fashion Weeks",
        "source_type": "curated",
        "base_url": None,
        "is_active": True,
        "sync_interval": 43200,  # monthly
    },
    {
        "name": "Wikipedia Albums",
        "source_type": "scrape",
        "base_url": "https://en.wikipedia.org/w/api.php",
        "api_key_env_var": "LASTFM_API_KEY",
        "is_active": True,
        "sync_interval": 10080,
    },
    {"name": "Manual", "source_type": "manual", "is_active": True},
]


async def main():
    async with async_session_maker() as session:
        # Seed categories (upsert: update existing slugs, insert new ones)
        for cat_data in CATEGORIES:
            existing = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            cat = existing.scalar_one_or_none()
            if cat:
                for key, value in cat_data.items():
                    setattr(cat, key, value)
            else:
                session.add(Category(**cat_data))
        await session.commit()
        print("Categories seeded.")

        # Seed data sources (upsert: update existing names, insert new ones)
        for src_data in DATA_SOURCES:
            existing = await session.execute(
                select(DataSource).where(DataSource.name == src_data["name"])
            )
            src = existing.scalar_one_or_none()
            if src:
                for key, value in src_data.items():
                    setattr(src, key, value)
            else:
                session.add(DataSource(**src_data))
        await session.commit()
        print("Data sources seeded.")

        # Seed superuser
        existing = await session.execute(
            select(User).where(User.email == settings.SUPERUSER_EMAIL)
        )
        if existing.scalar_one_or_none():
            print("Superuser already exists.")
        else:
            password_helper = PasswordHelper()
            hashed = password_helper.hash(settings.SUPERUSER_PASSWORD)
            user = User(
                id=uuid.uuid4(),
                email=settings.SUPERUSER_EMAIL,
                hashed_password=hashed,
                is_active=True,
                is_superuser=True,
                is_verified=True,
                display_name="Admin",
            )
            session.add(user)
            await session.commit()
            print(f"Superuser created: {settings.SUPERUSER_EMAIL}")


if __name__ == "__main__":
    asyncio.run(main())
