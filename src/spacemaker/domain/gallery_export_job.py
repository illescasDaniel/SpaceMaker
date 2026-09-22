from __future__ import annotations

from dataclasses import dataclass

from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase


@dataclass(slots=True)
class GalleryExportJob:
	job_id: str
	relative_path: str
	export_format: ExportFormat
	phase: ExportJobPhase
	percent: int
	download_path: str
	error: str
	skipped_encode: bool

	def to_dict(self) -> dict[str, object]:
		return {
			"job_id": self.job_id,
			"relative_path": self.relative_path,
			"format": self.export_format.value,
			"phase": self.phase.value,
			"percent": self.percent,
			"download_url": f"/api/gallery/export/{self.job_id}/file" if self.phase is ExportJobPhase.DONE else "",
			"error": self.error,
			"skipped_encode": self.skipped_encode,
		}
