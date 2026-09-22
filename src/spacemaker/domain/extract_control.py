from __future__ import annotations

import threading
from collections.abc import Callable


class ExtractJobControl:
	def __init__(self, *, on_paused: Callable[[], None] | None = None) -> None:
		self._cond = threading.Condition()
		self._on_paused = on_paused
		self._stop_queue = False
		self._paused = False
		self._pause_after_current = False
		self._stop_after_current = False

	def request_pause(self) -> None:
		with self._cond:
			self._pause_after_current = True

	def request_stop(self) -> None:
		with self._cond:
			self._stop_after_current = True
			self._stop_queue = True
			self._paused = False
			self._pause_after_current = False
			self._cond.notify_all()

	def resume(self) -> None:
		with self._cond:
			self._paused = False
			self._pause_after_current = False
			self._cond.notify_all()

	def was_stopped(self) -> bool:
		with self._cond:
			return self._stop_queue

	def is_paused(self) -> bool:
		with self._cond:
			return self._paused

	def before_next_file(self) -> bool:
		with self._cond:
			if self._stop_queue:
				return False
			while self._paused:
				self._cond.wait()
				if self._stop_queue:
					return False
			return True

	def after_file(self) -> None:
		with self._cond:
			if self._stop_after_current:
				self._stop_queue = True
				self._stop_after_current = False
			elif self._pause_after_current:
				self._pause_after_current = False
				self._paused = True
				if self._on_paused is not None:
					self._on_paused()
				self._cond.notify_all()
