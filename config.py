import os
from dataclasses import dataclass

@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    make_webhook_url: str = os.getenv("MAKE_WEBHOOK_URL", "")
    make_webhook_secret: str = os.getenv("MAKE_WEBHOOK_SECRET", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    google_drive_root_folder_id: str = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")
    media_dir: str = os.getenv("MEDIA_DIR", "./media")
    default_clips: int = int(os.getenv("DEFAULT_CLIPS", "3"))
    max_clip_seconds: int = int(os.getenv("MAX_CLIP_SECONDS", "90"))

settings = Settings()
