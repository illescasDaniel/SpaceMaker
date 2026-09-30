import { S } from "./state.ts";

export function isDesktopShell(): boolean {
	return S.clientShell === "desktop";
}

export function isMobileGalleryShell(): boolean {
	return S.clientShell === "mobile_gallery";
}

export function onClick(id: string, handler: (ev: MouseEvent) => void): void {
	const el = document.getElementById(id);
	if (el) {
		el.addEventListener("click", handler as EventListener);
	}
}

/** Every rejected `apiSend()` call lands here as `unknown` (strict `catch` typing);
 * this is the one place that turns it into UI copy. */
export function errorMessage(err: unknown, fallback: string): string {
	return err instanceof Error && err.message ? err.message : fallback;
}

/** Copy text for desktop shells where selection may be unavailable. */
export async function copyTextToClipboard(text: string): Promise<boolean> {
	if (!text) {
		return false;
	}
	try {
		if (navigator.clipboard?.writeText) {
			await navigator.clipboard.writeText(text);
			return true;
		}
	} catch {
		/* fall through */
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
	return ok;
}

export function isAbsolutePath(path: string): boolean {
	if (!path) {
		return false;
	}
	return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path);
}

export function showFormBanner(message: string, bannerId?: string): void {
	const banner = document.getElementById(bannerId || "form-banner");
	if (!banner) {
		return;
	}
	banner.textContent = message;
	banner.hidden = !message;
}

export function clearFormBanner(bannerId?: string): void {
	showFormBanner("", bannerId);
}

export function setStatusLine(el: HTMLElement | null, detailText: string): void {
	if (!el) {
		return;
	}
	el.textContent = "";
	const strong = document.createElement("strong");
	strong.textContent = "Status:";
	el.appendChild(strong);
	el.appendChild(document.createTextNode(" " + detailText));
}

export function bindDisclosure(btnId: string, panelId: string): void {
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

export function setQrUrlField(inputId: string, url: string): void {
	const input = document.getElementById(inputId);
	if (input instanceof HTMLInputElement) {
		input.value = url || "";
	}
}

export function setQrImage(img: HTMLImageElement | null, qrUrl: string, cacheKey?: string): void {
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
