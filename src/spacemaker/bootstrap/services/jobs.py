from __future__ import annotations

import contextlib
import logging
import time
import uuid
from typing import TYPE_CHECKING

from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.convert_policy import (
	ConvertStartPolicy,
	convert_start_policy,
	should_auto_drain_after_upload,
	should_promote_after_upload,
	should_requeue_convert_drain,
)
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase
from spacemaker.domain.gallery_export_job import GalleryExportJob
from spacemaker.domain.jobs import JobPhase, can_start_convert
from spacemaker.domain.library import JobProgress, LibraryFolder, TransferMode, live_job_progress
from spacemaker.domain.source_folders import SourceFolder, parse_source_folders


if TYPE_CHECKING:
	from spacemaker.bootstrap.services.core import AppServices


logger = logging.getLogger(__name__)


class JobsMixin:
	def push_state(self: AppServices) -> None:
		self.broadcast({"type": "state", "state": self.enriched_snapshot()})

	def push_gallery_export(self: AppServices, job: GalleryExportJob) -> None:
		self.broadcast({"type": "gallery_export", "export": job.to_dict()})

	def get_export_job(self: AppServices, job_id: str) -> GalleryExportJob | None:
		with self._export_lock:
			return self._export_jobs.get(job_id)

	def start_gallery_export(
		self: AppServices, library_root: str, relative_path: str, export_format: ExportFormat
	) -> GalleryExportJob:
		job_id = uuid.uuid4().hex
		job = GalleryExportJob(
			job_id=job_id,
			relative_path=relative_path,
			export_format=export_format,
			phase=ExportJobPhase.RUNNING,
			percent=0,
			download_path="",
			error="",
			skipped_encode=False,
		)
		with self._export_lock:
			self._export_jobs[job_id] = job
		self.push_gallery_export(job)
		self._executor.submit(self._run_gallery_export, library_root, job_id, relative_path, export_format)
		return job

	def _run_gallery_export(
		self: AppServices,
		library_root: str,
		job_id: str,
		relative_path: str,
		export_format: ExportFormat,
	) -> None:
		def on_progress(percent: int) -> None:
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.percent = percent
				job.phase = ExportJobPhase.RUNNING
			self.push_gallery_export(self._export_jobs[job_id])

		try:
			result = self.export_friendly.run(
				library_root,
				relative_path,
				export_format,
				on_progress=on_progress,
			)
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.phase = ExportJobPhase.DONE
				job.percent = 100
				job.download_path = result.download_path
				job.skipped_encode = result.skipped_encode
				job.error = ""
			self.push_gallery_export(self._export_jobs[job_id])
		except Exception as exc:
			logger.exception("Gallery export job crashed")
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.phase = ExportJobPhase.ERROR
				job.error = str(exc)
			self.push_gallery_export(self._export_jobs[job_id])

	def start_extract(self: AppServices) -> None:
		if self._extract_job_active():
			return
		with self.session._lock:
			if self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return
			method = self.session.connection_method
			if method is ConnectionMethod.WIFI:
				if not self.session.library_root:
					return
				self.session.transfer_mode = TransferMode.COPY
				self.session.extract_phase = JobPhase.RUNNING
				self.session.extract_progress = JobProgress(0, 0)
				self.session.last_error = ""
				library_root = self.session.library_root
				self.filesystem.ensure_library_folders(library_root)
			else:
				if not self.session.source_folders:
					return
				library_root = self.session.library_root
				device_id = self.session.device_id
				mode = self.session.transfer_mode
				folders = parse_source_folders(self.session.source_folders)
				self.session.extract_phase = JobPhase.RUNNING
				self.session.last_error = ""
		self._extract_control = ExtractJobControl(on_paused=self._on_extract_paused)
		if method is ConnectionMethod.WIFI:
			self._mint_wifi_token()
			self.push_state()
			return
		self.push_state()
		self._extract_future = self._executor.submit(
			self._run_extract,
			library_root,
			device_id,
			method,
			mode,
			folders,
		)

	def _on_extract_paused(self: AppServices) -> None:
		with self.session._lock:
			self.session.extract_phase = JobPhase.PAUSED
		self.push_state()

	def pause_extract(self: AppServices) -> None:
		with self.session._lock:
			is_wifi = self.session.connection_method is ConnectionMethod.WIFI
		if self._extract_control is not None:
			if is_wifi and self._wifi_uploads_in_flight == 0:
				self._extract_control.pause_immediately()
			else:
				self._extract_control.request_pause()

	def resume_extract(self: AppServices) -> None:
		with self.session._lock:
			if self.session.extract_phase is not JobPhase.PAUSED:
				return
			self.session.extract_phase = JobPhase.RUNNING
		if self._extract_control is not None:
			self._extract_control.resume()
		self.push_state()

	def stop_extract(self: AppServices) -> None:
		if self._extract_control is not None:
			self._extract_control.request_stop()
		was_wifi = False
		with self.session._lock:
			was_wifi = self.session.connection_method is ConnectionMethod.WIFI
			if was_wifi and self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.session.extract_phase = JobPhase.STOPPED
		if was_wifi:
			self._clear_wifi_token()
		self.push_state()

	def stop_extract_and_wait(self: AppServices, *, timeout_seconds: float = 300.0) -> None:
		future = self._extract_future
		with self.session._lock:
			phase_active = self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
		if not phase_active and (future is None or future.done()):
			return
		self.stop_extract()
		deadline = time.monotonic() + timeout_seconds
		while self._wifi_uploads_in_flight > 0 and time.monotonic() < deadline:
			time.sleep(0.05)
		future = self._extract_future
		if future is not None:
			remaining = deadline - time.monotonic()
			if remaining > 0:
				with contextlib.suppress(Exception):
					future.result(timeout=remaining)

	def stop_convert(self: AppServices) -> None:
		if self._convert_control is not None:
			self._convert_control.request_stop()
		self.push_state()

	def stop_convert_and_wait(self: AppServices, *, timeout_seconds: float = 300.0) -> None:
		future = self._convert_future
		if future is None or future.done():
			return
		self.stop_convert()
		remaining = timeout_seconds
		with contextlib.suppress(Exception):
			future.result(timeout=remaining)

	def _run_extract(
		self: AppServices,
		library_root: str,
		device_id: str,
		method: ConnectionMethod,
		mode: TransferMode,
		folders: frozenset[SourceFolder],
	) -> None:
		control = self._extract_control
		try:
			use_case = self.extract_use_case(method)

			def on_progress(progress: JobProgress) -> None:
				with self.session._lock:
					self.session.extract_progress = progress
				self.push_state()

			use_case.run(
				library_root,
				device_id,
				mode,
				source_folders=folders,
				control=control,
				on_progress=on_progress,
			)
			with self.session._lock:
				if control is not None and control.was_stopped():
					self.session.extract_phase = JobPhase.STOPPED
				elif control is not None and control.is_paused():
					self.session.extract_phase = JobPhase.PAUSED
				else:
					self.session.extract_phase = JobPhase.DONE
		except Exception as exc:
			logger.exception("Extract job crashed")
			with self.session._lock:
				self.session.extract_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._extract_future = None
		self.push_state()

	def ensure_easy_session(self: AppServices) -> None:
		with self.session._lock:
			self.session.active_module = AppModule.PHOTO_BACKUP
		self.bootstrap_photo_backup()

	def maybe_start_convert_drain(self: AppServices) -> None:
		# Call after each Wi‑Fi file lands (saved or size-skipped), not only after
		# the whole multipart request — so convert starts as soon as the first
		# photo arrives. While convert is already RUNNING, refresh the live total
		# (completed + originals remaining) instead of starting a second job.
		with self.session._lock:
			ui_mode = self.session.ui_mode
			convert_phase = self.session.convert_phase
			library_root = self.session.library_root
			completed = self.session.convert_progress.completed
		if not library_root:
			return
		originals = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
		if convert_phase is JobPhase.RUNNING:
			with self.session._lock:
				self.session.convert_progress = live_job_progress(completed, originals)
			self.push_state()
			return
		compress = self.compress_media_preference()
		if should_promote_after_upload(
			ui_mode=ui_mode,
			convert_phase=convert_phase,
			originals_count=originals,
			compress_media=compress.enabled,
		):
			self.promote_originals.run(library_root)
			self.run_coro(self.sync_gallery_index.run(library_root))
			self.push_state()
			return
		if not should_auto_drain_after_upload(
			ui_mode=ui_mode,
			convert_phase=convert_phase,
			originals_count=originals,
			compress_media=compress.enabled,
		):
			return
		self.start_convert(policy=ConvertStartPolicy.CONCURRENT_WITH_EXTRACT)

	def start_convert(self: AppServices, *, policy: ConvertStartPolicy | None = None) -> None:
		if self._convert_job_active():
			return
		with self.session._lock:
			library_root = self.session.library_root
			ui_mode = self.session.ui_mode
		if not library_root:
			return
		resolved = policy or convert_start_policy(ui_mode=ui_mode)
		if resolved is ConvertStartPolicy.STOP_EXTRACT_FIRST and self._extract_job_active():
			self.stop_extract_and_wait()
		with self.session._lock:
			originals = self.filesystem.count_files_in_folder(
				self.session.library_root,
				LibraryFolder.ORIGINALS,
			)
			if not can_start_convert(originals_count=originals, convert_job_active=False):
				return
			library_root = self.session.library_root
			self.session.convert_phase = JobPhase.RUNNING
			self.session.convert_progress = live_job_progress(0, originals)
			self.session.last_error = ""
			concurrent = resolved is ConvertStartPolicy.CONCURRENT_WITH_EXTRACT
		self._convert_control = ExtractJobControl()
		self.push_state()
		self._convert_future = self._executor.submit(
			self._run_convert,
			library_root,
			concurrent_with_extract=concurrent,
		)

	def _run_convert(self: AppServices, library_root: str, *, concurrent_with_extract: bool = False) -> None:
		control = self._convert_control
		self.run_coro(self.sync_gallery_index.run(library_root))
		try:
			use_case = self.convert_use_case()
			cumulative_completed = 0

			while True:
				# Each use_case.run() call scans originals/ fresh and reports progress
				# starting from (0, <files in that scan>). Offset by everything already
				# completed in earlier drain passes, then recompute total live from
				# originals remaining so mid-pass uploads bump the displayed total.
				base_completed = cumulative_completed

				def on_progress(progress: JobProgress, *, _base: int = base_completed) -> None:
					remaining = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
					with self.session._lock:
						self.session.convert_progress = live_job_progress(
							_base + progress.completed,
							remaining,
						)
					self.push_state()

				batch_progress = use_case.run(library_root, control=control, on_progress=on_progress)
				cumulative_completed += batch_progress.completed
				with self.session._lock:
					remaining = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
					extract_phase = self.session.extract_phase
				# Files uploaded while this same job was converting land in originals/
				# after use_case.run()'s own scan started, so drain them here in a loop
				# rather than recursing into start_convert(): that would re-enter while
				# self._convert_future (this job) is still not-done, so
				# _convert_job_active() would block it from actually starting anything.
				if not (
					(control is None or not control.was_stopped())
					and self.compress_media_preference().enabled
					and should_requeue_convert_drain(
						concurrent_with_extract=concurrent_with_extract,
						remaining_originals=remaining,
					)
				):
					break
				with self.session._lock:
					self.session.convert_progress = live_job_progress(cumulative_completed, remaining)
				self.run_coro(self.sync_gallery_index.run(library_root))
				self.push_state()
			progress = live_job_progress(cumulative_completed, remaining)
			with self.session._lock:
				if batch_progress.total == 0 and remaining > 0:
					self.session.convert_phase = JobPhase.ERROR
					self.session.last_error = (
						f"convert found no files under {library_root}/originals "
						f"({remaining} file(s) still on disk — check library path)"
					)
				elif (
					concurrent_with_extract and remaining == 0 and extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}
				):
					self.session.convert_phase = JobPhase.IDLE
					self.session.convert_progress = progress
					self.session.last_error = ""
				elif control is not None and control.was_stopped():
					self.session.convert_phase = JobPhase.STOPPED
					self.session.convert_progress = progress
					self.session.last_error = ""
				else:
					self.session.convert_phase = JobPhase.DONE
					self.session.convert_progress = progress
					error_count = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ERROR)
					invalid_count = self.filesystem.count_files_in_folder(library_root, LibraryFolder.INVALID)
					if error_count or invalid_count:
						parts: list[str] = []
						if error_count:
							parts.append(f"{error_count} in error/")
						if invalid_count:
							parts.append(f"{invalid_count} in invalid/")
						hint = use_case.last_failure or "Check tools/ (magick, ffmpeg) and file formats."
						self.session.last_error = f"Convert finished with {', '.join(parts)}. Last failure: {hint}"
					else:
						self.session.last_error = ""
		except Exception as exc:
			logger.exception("Convert job crashed")
			with self.session._lock:
				self.session.convert_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		finally:
			self._convert_future = None
		self.run_coro(self.sync_gallery_index.run(library_root))
		self.push_state()
