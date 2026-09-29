from __future__ import annotations

import sys

from fastapi import APIRouter, HTTPException, Request

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.models import UsbTransferExtrasBody
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.connection import ConnectionMethod


def build_usb_transfer_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.post("/api/usb-transfer/start")
	def usb_transfer_start(request: Request) -> dict[str, object]:
		require_loopback(request)
		method = services.session.connection_method
		if method is ConnectionMethod.WIFI:
			raise HTTPException(status_code=400, detail="USB file transfer requires ADB or iPhone USB")
		if method is ConnectionMethod.AFC and sys.platform != "linux":
			raise HTTPException(status_code=501, detail="iPhone USB is Linux only in this release")
		if not services.session.device_id:
			raise HTTPException(status_code=400, detail="select a device")
		if not services.session.transfer_folders and not services.session.transfer_extra_paths:
			raise HTTPException(status_code=400, detail="select at least one folder or Browse source")
		services.start_usb_transfer()
		return services.enriched_snapshot()

	@router.post("/api/usb-transfer/extras")
	def usb_transfer_add_extras(request: Request, body: UsbTransferExtrasBody) -> dict[str, object]:
		require_loopback(request)
		try:
			services.add_usb_transfer_extras_from_host(body.host_paths)
		except ValueError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		services.push_state()
		return services.enriched_snapshot()

	@router.post("/api/usb-transfer/mount")
	def usb_transfer_mount(request: Request) -> dict[str, object]:
		"""Lazy adbfs/ifuse mount for Browse (avoids mounting on every state snapshot)."""
		require_loopback(request)
		try:
			services.ensure_usb_browse_mount()
		except ValueError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		except RuntimeError as exc:
			raise HTTPException(status_code=503, detail=str(exc)) from exc
		services.push_state()
		return services.enriched_snapshot()

	@router.delete("/api/usb-transfer/extras")
	def usb_transfer_clear_extras(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.clear_usb_transfer_extras()
		services.push_state()
		return services.enriched_snapshot()

	@router.post("/api/usb-transfer/pause")
	def usb_transfer_pause(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.pause_usb_transfer()
		return services.enriched_snapshot()

	@router.post("/api/usb-transfer/resume")
	def usb_transfer_resume(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.resume_usb_transfer()
		return services.enriched_snapshot()

	@router.post("/api/usb-transfer/stop")
	def usb_transfer_stop(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.stop_usb_transfer_and_wait(timeout_seconds=300.0)
		return services.enriched_snapshot()

	return router
