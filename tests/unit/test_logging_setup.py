import logging
from pathlib import Path

from spacemaker.bootstrap.logging_setup import configure_logging


def test_given_tools_dir_when_configure_logging_then_creates_log_file(tmp_path: Path) -> None:
	# given
	tools_dir = tmp_path / "tools_root" / "tools"
	# when
	log_path = configure_logging(tools_dir=tools_dir)
	# then
	assert log_path == tmp_path / "tools_root" / "logs" / "spacemaker.log"
	assert log_path.is_file()


def test_given_same_tools_dir_when_configure_logging_twice_then_attaches_one_handler(tmp_path: Path) -> None:
	# given
	tools_dir = tmp_path / "tools_root" / "tools"
	root_logger = logging.getLogger("spacemaker")
	# when
	first_path = configure_logging(tools_dir=tools_dir)
	handlers_after_first = [h for h in root_logger.handlers if getattr(h, "baseFilename", None) == str(first_path)]
	second_path = configure_logging(tools_dir=tools_dir)
	handlers_after_second = [h for h in root_logger.handlers if getattr(h, "baseFilename", None) == str(second_path)]
	# then
	assert first_path == second_path
	assert len(handlers_after_first) == 1
	assert len(handlers_after_second) == 1


def test_given_configured_logging_when_module_logger_emits_then_record_reaches_file(tmp_path: Path) -> None:
	# given
	tools_dir = tmp_path / "tools_root" / "tools"
	log_path = configure_logging(tools_dir=tools_dir)
	logger = logging.getLogger("spacemaker.application.convert_media")
	# when
	logger.warning("relative/path.png: encoded output failed validation")
	for handler in logging.getLogger("spacemaker").handlers:
		handler.flush()
	# then
	text = log_path.read_text(encoding="utf-8")
	assert "relative/path.png: encoded output failed validation" in text
