import logging
import sys

def configure_logging(level_name: str = "INFO"):
    logger = logging.getLogger("chikguard")

    # Check if a handler already exists so we don't duplicate them
    if not logger.handlers:
        level = getattr(logging, level_name.upper(), logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
