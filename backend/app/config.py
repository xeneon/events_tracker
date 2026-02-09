from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://events_user:events_password@192.168.1.103:5432/events_tracker"
    JWT_SECRET: str = "change-me-to-a-random-secret-key"

    SUPERUSER_EMAIL: str = "admin@example.com"
    SUPERUSER_PASSWORD: str = "changeme123"

    CALENDARIFIC_API_KEY: str = ""
    TRAKT_CLIENT_ID: str = ""
    LASTFM_API_KEY: str = ""

    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://192.168.1.102:3000,http://192.168.1.102"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
