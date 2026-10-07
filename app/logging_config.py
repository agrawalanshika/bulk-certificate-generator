import logging

from app.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT)
    root.setLevel(level)