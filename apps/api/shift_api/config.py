from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHIFT_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./shift.sqlite"
    demo_mode: bool = True
    supabase_url: str = ""
    jwt_audience: str = "authenticated"

    # Shift V1 sessions and Google integration. Empty Google keys keep the local
    # demo sign-in path; nothing contacts Google until both keys are set.
    session_secret: str = ""
    cookie_secure: bool = False
    public_base_url: str = "http://127.0.0.1:3000"
    google_client_id: str = ""
    google_client_secret: str = ""
    # Fernet key (urlsafe base64, 32 bytes) used to encrypt Google refresh tokens.
    token_encryption_key: str = ""
    upload_dir: str = "./.data/uploads"


settings = Settings()
