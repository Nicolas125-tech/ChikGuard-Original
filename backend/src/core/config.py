import os
from dotenv import load_dotenv
load_dotenv()
import secrets

class Settings:
    def __init__(self):
        # Database setup
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///chikguard.db")
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))

        # Application settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.flask_host = os.getenv("FLASK_HOST", "0.0.0.0")
        self.flask_port = int(os.getenv("FLASK_PORT", "5000"))
        self.app_env = os.getenv("ENV", "development")

        # Telemetry/Hardware
        self.camera_index = int(os.getenv("CAMERA_INDEX", "0"))

        # Alerts and telegram
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", None)
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", None)

def load_settings():
    return Settings()
