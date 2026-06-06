from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # TMDB
    tmdb_api_key: str

    # Database
    database_url: str = "postgresql+asyncpg://ncrawler:ncrawler@postgres:5432/ncrawler"

    # qBittorrent
    qbittorrent_host: str = "qbittorrent"
    qbittorrent_port: int = 8080
    qbittorrent_username: str = "admin"
    qbittorrent_password: str = "adminadmin"

    # Library paths
    movies_root: str = "/library/movies"
    series_root: str = "/library/series"
    downloads_path: str = "/downloads"

    # Scheduler
    discovery_interval_hours: int = 168  # weekly

    # Quality preference
    preferred_quality: str = "1080p"

    # API authentication (empty string = no auth — dev mode only)
    api_key: str = ""


settings = Settings()
