import logging

logger = logging.getLogger(__name__)

class AlertProvider:
    def __init__(self, settings):
        self.settings = settings

    def send(self, message):
        """
        Send an alert. In a real system, this might use Telegram, Email,
        or SMS APIs. For now, we log it to standard output.
        """
        logger.info(f"[ALERT] {message}")
        # Assuming return value True means success
        return True

def build_alert_provider(settings):
    """
    Factory function to build the alert provider.
    """
    return AlertProvider(settings)
