from typing import Literal
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHIFT_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./shift.sqlite"
    demo_mode: bool = False
    environment: Literal["local", "hosted"] = "hosted"
    supabase_url: str = ""
    jwt_audience: str = "authenticated"

    def validate_hosted(self):
        if self.demo_mode:
            if self.environment != "local":
                raise ValueError("Demo mode requires SHIFT_ENVIRONMENT=local")
            return
        if not self.database_url.startswith("postgresql"):
            raise ValueError("Hosted mode requires PostgreSQL")
        parsed = urlparse(self.supabase_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
            raise ValueError("Hosted mode requires SHIFT_SUPABASE_URL (HTTPS origin)")
        if not self.jwt_audience:
            raise ValueError("Hosted mode requires a JWT audience")

    @property
    def issuer(self):
        return self.supabase_url.rstrip("/") + "/auth/v1"


settings = Settings()
