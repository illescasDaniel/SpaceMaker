from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Protocol

from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.device.factory import device_repository_for
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.adapters.outbound.media.subprocess_converter import SubprocessMediaConverter
from spacemaker.adapters.outbound.media.subprocess_probe import SubprocessMediaProbe
from spacemaker.adapters.outbound.media.subprocess_thumbnails import SubprocessThumbnailGenerator
from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.application.convert_media import ConvertMedia
from spacemaker.application.error_recovery import ErrorRecovery
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.application.extract_media import ExtractMedia
from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.application.get_gallery_item import GetGalleryItem
from spacemaker.application.wizard_state import wizard_actions
from spacemaker.bootstrap.bundled_tools import missing_bundled_tools
from spacemaker.bootstrap.paths import default_library_root, normalize_library_root
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase
from spacemaker.domain.gallery_export_job import GalleryExportJob
from spacemaker.domain.jobs import JobPhase, can_start_convert
from spacemaker.domain.library import JobProgress, LibraryFolder, TransferMode
from spacemaker.domain.source_folders import SourceFolder, parse_source_folders


class WebSocketLike(Protocol):
	async def send_json(self, data: dict[str, object]) -> None: ...


def repo_root() -> Path:
	return Path(__file__).resolve().parents[3]


class AppServices:
	def __init__(self, *, port: int = 8765, bind_host: str = "0.0.0.0") -> None:
		self.port = port
		self.bind_host = bind_host
		self._captured_at_cache_key = ""
		self._captured_at_cache: dict[str, datetime] = {}
		self.session = AppSession(library_root=normalize_library_root(default_library_root()))
		self.filesystem = LocalFileSystem()
		self.runner = ToolRunner()
		self.probe = SubprocessMediaProbe(self.runner)
		self.converter = SubprocessMediaConverter(self.runner)
		self.error_recovery = ErrorRecovery(self.filesystem)
		self.gallery = GenerateGallery(self.filesystem)
		self.get_gallery_item = GetGalleryItem(self.filesystem, self.probe)
		self.export_friendly = ExportFriendlyMedia(self.filesystem, self.converter, self.probe)
		self.thumbnails = SubprocessThumbnailGenerator(self.runner)
		self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="spacemaker-job")
		self._export_jobs: dict[str, GalleryExportJob] = {}
		self._export_lock = threading.Lock()
		self._ws_clients: set[WebSocketLike] = set()
		self._ws_lock = threading.Lock()
		self._event_loop: asyncio.AbstractEventLoop | None = None
		self._extract_control: ExtractJobControl | None = None

	def devices_for(self, method: ConnectionMethod):
		return device_repository_for(method, runner=self.runner)

	def extract_use_case(self, method: ConnectionMethod) -> ExtractMedia:
		return ExtractMedia(self.devices_for(method), self.filesystem)

	def convert_use_case(self) -> ConvertMedia:
		return ConvertMedia(self.filesystem, self.converter, self.probe)

	def folder_counts(self, library_root: str) -> dict[str, int]:
		if not library_root:
			return {f.value: 0 for f in LibraryFolder}
		return {f.value: self.filesystem.count_files_in_folder(library_root, f) for f in LibraryFolder}

	def invalidate_gallery_metadata_cache(self) -> None:
		self._captured_at_cache_key = ""
		self._captured_at_cache = {}

	def captured_at_map(self, library_root: str) -> dict[str, datetime]:
		if not library_root:
			return {}
		if library_root == self._captured_at_cache_key and self._captured_at_cache:
			return self._captured_at_cache
		root = self.filesystem.library_path(library_root, LibraryFolder.CONVERTED, "")
		paths = self.filesystem.list_files_recursive(root)
		out: dict[str, datetime] = {}
		for rel in paths:
			full = Path(self.filesystem.library_path(library_root, LibraryFolder.CONVERTED, rel))
			if not full.is_file():
				continue
			captured = self.probe.captured_at(str(full))
			out[rel] = captured if captured is not None else datetime.fromtimestamp(full.stat().st_mtime)
		self._captured_at_cache_key = library_root
		self._captured_at_cache = out
		return out

	def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
		self._event_loop = loop

	def register_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.add(ws)

	def unregister_ws(self, ws: WebSocketLike) -> None:
		with self._ws_lock:
			self._ws_clients.discard(ws)

	def broadcast(self, payload: dict[str, object]) -> None:
		loop = self._event_loop
		if loop is None:
			return
		with self._ws_lock:
			clients = list(self._ws_clients)
		for ws in clients:
			try:
				asyncio.run_coroutine_threadsafe(ws.send_json(payload), loop)
			except Exception:
				self.unregister_ws(ws)

	def reconcile_device_selection(self, connection_method: ConnectionMethod | None = None) -> bool:
		method = connection_method or self.session.connection_method
		try:
			known = {d.device_id: d.label for d in self.devices_for(method).list_devices()}
		except FileNotFoundError:
			known = {}
		changed = False
		with self.session._lock:
			if method is not self.session.connection_method:
				return False
			if self.session.device_id and self.session.device_id not in known:
				self.session.device_id = ""
				self.session.device_label = ""
				changed = True
			elif self.session.device_id in known and self.session.device_label != known[self.session.device_id]:
				self.session.device_label = known[self.session.device_id]
				changed = True
		return changed

	def enriched_snapshot(self) -> dict[str, object]:
		base = self.session.snapshot()
		with self.session._lock:
			folders = list(self.session.source_folders)
			has_folders = len(folders) > 0
			has_device = bool(self.session.device_id)
			extract_phase = self.session.extract_phase
			convert_phase = self.session.convert_phase
			convert_percent = self.session.convert_progress.percent
			library_root = self.session.library_root
		actions = wizard_actions(
			extract_phase=extract_phase,
			convert_phase=convert_phase,
			convert_progress_percent=convert_percent,
			library_root=library_root,
			count_in_folder=self.filesystem.count_files_in_folder,
			has_device=has_device,
			has_source_folders=has_folders,
		)
		base.update(actions)
		counts = self.folder_counts(library_root) if library_root else {f.value: 0 for f in LibraryFolder}
		base["library_counts"] = counts
		base["missing_tools"] = missing_bundled_tools()
		return base

	def push_state(self) -> None:
		self.broadcast({"type": "state", "state": self.enriched_snapshot()})

	def push_gallery_export(self, job: GalleryExportJob) -> None:
		self.broadcast({"type": "gallery_export", "export": job.to_dict()})

	def get_export_job(self, job_id: str) -> GalleryExportJob | None:
		with self._export_lock:
			return self._export_jobs.get(job_id)

	def start_gallery_export(
		self, library_root: str, relative_path: str, export_format: ExportFormat
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
		self,
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
			with self._export_lock:
				job = self._export_jobs.get(job_id)
				if job is None:
					return
				job.phase = ExportJobPhase.ERROR
				job.error = str(exc)
			self.push_gallery_export(self._export_jobs[job_id])

	def start_extract(self) -> None:
		with self.session._lock:
			if self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				return
			if not self.session.source_folders:
				return
			library_root = self.session.library_root
			device_id = self.session.device_id
			method = self.session.connection_method
			mode = self.session.transfer_mode
			folders = parse_source_folders(self.session.source_folders)
			self.session.extract_phase = JobPhase.RUNNING
			self.session.last_error = ""
		self._extract_control = ExtractJobControl(on_paused=self._on_extract_paused)
		self.push_state()
		self._executor.submit(self._run_extract, library_root, device_id, method, mode, folders)

	def _on_extract_paused(self) -> None:
		with self.session._lock:
			self.session.extract_phase = JobPhase.PAUSED
		self.push_state()

	def pause_extract(self) -> None:
		if self._extract_control is not None:
			self._extract_control.request_pause()

	def resume_extract(self) -> None:
		with self.session._lock:
			if self.session.extract_phase is not JobPhase.PAUSED:
				return
			self.session.extract_phase = JobPhase.RUNNING
		if self._extract_control is not None:
			self._extract_control.resume()
		self.push_state()

	def stop_extract(self) -> None:
		if self._extract_control is not None:
			self._extract_control.request_stop()
		with self.session._lock:
			if self.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				self.session.extract_phase = JobPhase.STOPPED
		self.push_state()

	def _run_extract(
		self,
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
				if self.session.extract_phase is JobPhase.STOPPED or (control is not None and control.was_stopped()):
					self.session.extract_phase = JobPhase.STOPPED
				elif control is not None and control.is_paused():
					self.session.extract_phase = JobPhase.PAUSED
				else:
					self.session.extract_phase = JobPhase.DONE
		except Exception as exc:
			with self.session._lock:
				self.session.extract_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		self.push_state()

	def start_convert(self) -> None:
		with self.session._lock:
			if self.session.convert_phase is JobPhase.RUNNING:
				return
			originals = self.filesystem.count_files_in_folder(
				self.session.library_root,
				LibraryFolder.ORIGINALS,
			)
			if not can_start_convert(extract_phase=self.session.extract_phase, originals_count=originals):
				return
			library_root = self.session.library_root
			self.session.convert_phase = JobPhase.RUNNING
			self.session.convert_progress = JobProgress(0, originals)
			self.session.last_error = ""
		self.push_state()
		self._executor.submit(self._run_convert, library_root)

	def _run_convert(self, library_root: str) -> None:
		self.invalidate_gallery_metadata_cache()
		try:
			use_case = self.convert_use_case()

			def on_progress(progress: JobProgress) -> None:
				with self.session._lock:
					self.session.convert_progress = progress
				self.push_state()

			progress = use_case.run(library_root, on_progress=on_progress)
			with self.session._lock:
				remaining = self.filesystem.count_files_in_folder(library_root, LibraryFolder.ORIGINALS)
				if progress.total == 0 and remaining > 0:
					self.session.convert_phase = JobPhase.ERROR
					self.session.last_error = (
						f"convert found no files under {library_root}/originals "
						f"({remaining} file(s) still on disk — check library path)"
					)
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
			with self.session._lock:
				self.session.convert_phase = JobPhase.ERROR
				self.session.last_error = str(exc)
		self.invalidate_gallery_metadata_cache()
		self.push_state()


def create_app(*, port: int = 8765, bind_host: str = "0.0.0.0"):
	from spacemaker.adapters.inbound.web.app import create_fastapi_app

	services = AppServices(port=port, bind_host=bind_host)
	app = create_fastapi_app(services)
	return app
