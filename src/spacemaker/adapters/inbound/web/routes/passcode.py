from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.models import PasscodeBody, UnlockBody
from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.network_passcode import PasscodeTooShortError, UnlockOutcome, UnlockResult


LOGIN_COOKIE = "spacemaker_login"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 10


def build_passcode_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	def _passcode() -> NetworkPasscode:
		passcode = services.network_passcode
		if passcode is None:
			raise HTTPException(status_code=503, detail="network passcode unavailable")
		return passcode

	def _status() -> dict[str, bool]:
		passcode = _passcode()
		return {"enabled": passcode.enabled, "corrupt_warning": passcode.corrupt_warning}

	@router.get("/api/network-passcode")
	def passcode_status(request: Request) -> dict[str, bool]:
		require_loopback(request)
		return _status()

	@router.put("/api/network-passcode")
	def passcode_set(request: Request, body: PasscodeBody) -> dict[str, bool]:
		require_loopback(request)
		try:
			_passcode().set_passcode(body.passcode)
		except PasscodeTooShortError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		services.push_state()
		return _status()

	@router.delete("/api/network-passcode")
	def passcode_clear(request: Request) -> dict[str, bool]:
		require_loopback(request)
		_passcode().clear()
		services.push_state()
		return _status()

	@router.post("/api/unlock")
	def unlock(request: Request, body: UnlockBody) -> JSONResponse:
		passcode = _passcode()
		client_id = request.client.host if request.client else "unknown"
		result: UnlockResult
		if body.token:
			result = passcode.unlock_with_token(client_id, body.token)
		else:
			result = passcode.unlock_with_passcode(client_id, body.passcode or "")
		if result.outcome is UnlockOutcome.LOCKED_OUT:
			return JSONResponse(
				{"detail": "locked-out", "retry_after_seconds": result.retry_after_seconds},
				status_code=429,
				headers={"Retry-After": str(result.retry_after_seconds)},
			)
		if result.outcome is UnlockOutcome.WRONG:
			return JSONResponse({"detail": "wrong-passcode"}, status_code=401)
		response = JSONResponse({"ok": True})
		if result.login:
			response.set_cookie(
				LOGIN_COOKIE,
				result.login,
				max_age=_COOKIE_MAX_AGE,
				httponly=True,
				samesite="strict",
				path="/",
			)
		return response

	return router
