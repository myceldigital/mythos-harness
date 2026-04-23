from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=getattr(logging, level, logging.INFO))
    else:
        root.setLevel(getattr(logging, level, logging.INFO))
