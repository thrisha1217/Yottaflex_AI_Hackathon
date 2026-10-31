"""
backend/config.py

Application settings loaded from environment variables with secure defaults
for local development. Uses pydantic-settings BaseSettings so any variable
can be overridden by a .env file or a real environment variable.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # MySQL connection string — points to local instance by default.
    DATABASE_URL: str = (
        "mysql+mysqlconnector://root:password@localhost:3306/academic_integrity"
    )

    # Allowed CORS origins — covers the two common React dev-server ports.
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance imported throughout the application.
settings = Settings()
