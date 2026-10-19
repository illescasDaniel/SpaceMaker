import { S } from "./state.js";
export function isDesktopShell() {
	return S.clientShell === "desktop";
}
export function isMobileGalleryShell() {
	return S.clientShell === "mobile_gallery";
}
export function onClick(id, handler) {
	const el = document.getElementById(id);
	if (el) {
		el.addEventListener("click", handler);
	}
}
/** Every rejected `apiSend()` call lands here as `unknown` (strict `catch` typing);
 * this is the one place that turns it into UI copy. */
export function errorMessage(err, fallback) {
	return err instanceof Error && err.message ? err.message : fallback;
}
/**
 * Copy text for desktop shells where selection may be unavailable. `execCommand("copy")` goes first: it needs
 * no permission, whereas `navigator.clipboard` makes QtWebEngine raise a permission request that pywebview's
 * Qt backend answers with an invalid policy type (TypeError), so it is only a fallback.
 */
export async function copyTextToClipboard(text) {
	if (!text) {
		return false;
	}
	const area = document.createElement("textarea");
	area.value = text;
	area.setAttribute("readonly", "");
	area.style.position = "fixed";
	area.style.left = "-9999px";
	document.body.appendChild(area);
	area.select();
	let ok = false;
	try {
		ok = document.execCommand("copy");
	} catch {
		ok = false;
	}
	area.remove();
	if (ok) {
		return true;
	}
	if (navigator.clipboard && window.isSecureContext) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch {
			return false;
		}
	}
	return false;
}
export function isAbsolutePath(path) {
	if (!path) {
		return false;
	}
	return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path);
}
export function showFormBanner(message, bannerId) {
	const banner = document.getElementById(bannerId || "form-banner");
	if (!banner) {
		return;
	}
	banner.textContent = message;
	banner.hidden = !message;
}
export function clearFormBanner(bannerId) {
	showFormBanner("", bannerId);
}
export function setStatusLine(el, detailText) {
	if (!el) {
		return;
	}
	el.textContent = "";
	const strong = document.createElement("strong");
	strong.textContent = "Status:";
	el.appendChild(strong);
	el.appendChild(document.createTextNode(" " + detailText));
}
export function setQrImage(img, qrUrl, cacheKey) {
	if (!img) {
		return;
	}
	const key = cacheKey || img.id || "qr";
	if (!qrUrl) {
		img.removeAttribute("src");
		delete S.lastQrSrcByElementId[key];
		return;
	}
	if (S.lastQrSrcByElementId[key] === qrUrl) {
		return;
	}
	S.lastQrSrcByElementId[key] = qrUrl;
	img.src = qrUrl;
}
/** Percent-encode each path segment (keeps `/`, but escapes `#`, `?`, `%` that `encodeURI` leaves alone). */
export function encodePathSegments(path) {
	return path.split("/").map(encodeURIComponent).join("/");
}
