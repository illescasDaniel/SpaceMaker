import { R, S } from "./state.js";
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
export function bindDisclosure(btnId, panelId) {
	const btn = document.getElementById(btnId);
	const panel = document.getElementById(panelId);
	if (!btn || !panel) {
		return;
	}
	btn.addEventListener("click", () => {
		const open = panel.hasAttribute("hidden");
		panel.toggleAttribute("hidden", !open);
		btn.setAttribute("aria-expanded", open ? "true" : "false");
	});
}
export function setQrUrlField(inputId, url) {
	const input = document.getElementById(inputId);
	if (input instanceof HTMLInputElement) {
		input.value = url || "";
	}
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
R.isDesktopShell = isDesktopShell;
R.isMobileGalleryShell = isMobileGalleryShell;
R.onClick = onClick;
R.isAbsolutePath = isAbsolutePath;
R.showFormBanner = showFormBanner;
R.clearFormBanner = clearFormBanner;
R.setStatusLine = setStatusLine;
R.bindDisclosure = bindDisclosure;
/** Feature modules still call the pre-rename names. */
R.bindInfoPanelToggle = bindDisclosure;
R.setQrUrlField = setQrUrlField;
R.setQrImage = setQrImage;
R.setQrImageSrc = setQrImage;
