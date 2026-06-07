from __future__ import annotations

import logging
import os

logging.getLogger(__name__).addHandler(logging.NullHandler())

from md24de_mcp.server import mcp  # noqa: E402


def main() -> None:
    """Entry point for the ``md24de-mcp`` script."""
    log_level = getattr(logging, os.environ.get("LOG_LEVEL", "WARNING").upper(), logging.WARNING)
    logging.basicConfig(level=log_level)
    logging.getLogger("md24de").setLevel(log_level)
    if log_level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
    mcp.run()


__all__ = ["main", "mcp"]
