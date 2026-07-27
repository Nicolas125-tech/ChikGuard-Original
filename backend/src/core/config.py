import os

from dotenv import load_dotenv

load_dotenv()
import secrets


class Settings:
    def __init__(self):
        # Database setup
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///chikguard.db")
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.jwt_secret_key:
            if os.getenv("ENV") == "production" or os.getenv("FLASK_ENV") == "production":
                raise ValueError("JWT_SECRET_KEY environment variable MUST be set in production")
            else:
                # Fallback to a static dev secret to avoid token invalidation across restarts
                self.jwt_secret_key = "dev-secret-key-change-in-production-long-enough"

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

        # Twilio settings
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", None)
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", None)
        self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER", None)
        self.twilio_to_number = os.getenv("TWILIO_TO_NUMBER", None)

        # SMTP settings
        self.smtp_server = os.getenv("SMTP_SERVER", None)
        self.smtp_port = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else 587
        self.smtp_user = os.getenv("SMTP_USER", None)
        self.smtp_password = os.getenv("SMTP_PASSWORD", None)
        self.smtp_to = os.getenv("SMTP_TO", None)


def load_settings():
    return Settings()
