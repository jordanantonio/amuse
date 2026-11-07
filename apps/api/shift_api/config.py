from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHIFT_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./shift.sqlite"
    demo_mode: bool = True
    supabase_url: str = ""
    jwt_audience: str = "authenticated"


settings = Settings()
