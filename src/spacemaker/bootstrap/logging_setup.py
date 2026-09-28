from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from spacemaker.bootstrap.paths import spacemaker_data_dir


_LOG_FILE_NAME = "spacemaker.log"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_root_logger = logging.getLogger("spacemaker")
_configured_paths: set[Path] = set()


def configure_logging(*, tools_dir: Path | None = None, level: int = logging.INFO) -> Path:
	"""Attach a rotating file handler to the "spacemaker" logger, once per log path.

	Every module's ``logging.getLogger(__name__)`` lives under the ``spacemaker.*``
	name and propagates up to this one handler, so this is the only setup needed.
	"""
	log_path = spacemaker_data_dir(tools_dir=tools_dir) / "logs" / _LOG_FILE_NAME
	if log_path in _configured_paths:
		return log_path
	log_path.parent.mkdir(parents=True, exist_ok=True)
	handler = RotatingFileHandler(log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8")
	handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
	_root_logger.addHandler(handler)
	_root_logger.setLevel(level)
	_configured_paths.add(log_path)
	return log_path
