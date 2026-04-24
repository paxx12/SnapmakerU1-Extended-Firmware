"""Process entry point: argparse, logging, and the threaded HTTP server."""

import argparse
import logging
import logging.handlers
import os
from http.server import ThreadingHTTPServer

from .constants import LOG_FILE
from .handler import RequestHandler


def setup_logging():
    """Configure root logger with stream + daily-rotated file handler."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.TimedRotatingFileHandler(
            LOG_FILE, when="midnight", interval=1, backupCount=7
        ),
    ]
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in handlers:
        h.setFormatter(fmt)
    logging.root.handlers = handlers
    logging.root.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser(description="RFID Spools Management API")
    parser.add_argument("--bind", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8093, help="Listen port")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting RFID Spools API on %s:%d", args.bind, args.port)

    server = ThreadingHTTPServer((args.bind, args.port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("RFID Spools API stopped")


if __name__ == "__main__":
    main()
