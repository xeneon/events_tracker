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
    {"name": "Public Holiday", "slug": "public-holiday", "color": "#ef4444", "icon": "calendar", "sort_order": 1},
    {"name": "Sports", "slug": "sports", "color": "#22c55e", "icon": "trophy", "sort_order": 2},
    {"name": "Movie Release", "slug": "movie-release", "color": "#a855f7", "icon": "film", "sort_order": 3},
    {"name": "Game Release", "slug": "game-release", "color": "#3b82f6", "icon": "gamepad", "sort_order": 4},
    {"name": "Political", "slug": "political", "color": "#f97316", "icon": "landmark", "sort_order": 5},
    {"name": "Other", "slug": "other", "color": "#6b7280", "icon": "circle", "sort_order": 6},
]

DATA_SOURCES = [
    {"name": "Nager.Date", "source_type": "api", "base_url": "https://date.nager.at/api/v3", "is_active": True, "sync_interval": 1440},
    {"name": "TheSportsDB", "source_type": "api", "base_url": "https://www.thesportsdb.com/api/v1/json", "is_active": True, "sync_interval": 360},
    {"name": "TMDB", "source_type": "api", "base_url": "https://api.themoviedb.org/3", "api_key_env_var": "TMDB_API_KEY", "is_active": True, "sync_interval": 1440},
    {"name": "RAWG", "source_type": "api", "base_url": "https://api.rawg.io/api", "api_key_env_var": "RAWG_API_KEY", "is_active": True, "sync_interval": 1440},
    {"name": "GDELT", "source_type": "api", "base_url": "https://api.gdeltproject.org", "is_active": True, "sync_interval": 10080},
    {"name": "Manual", "source_type": "manual", "is_active": True},
]


async def main():
    async with async_session_maker() as session:
        # Seed categories
        for cat_data in CATEGORIES:
            existing = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            if not existing.scalar_one_or_none():
                session.add(Category(**cat_data))
        await session.commit()
        print("Categories seeded.")

        # Seed data sources
        for src_data in DATA_SOURCES:
            existing = await session.execute(
                select(DataSource).where(DataSource.name == src_data["name"])
            )
            if not existing.scalar_one_or_none():
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
