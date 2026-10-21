/** Lightbox for the phone picker's photo previews (`#dp-lb`): browse image rows, tick them, see the large rendition. */

import {
	buildPreviewUrl,
	formatMediaDuration,
	outcomeForStatus,
	type PreviewTarget,
	stepIndex,
} from "./device-preview.ts";

/** One image row as the lightbox sees it. */
interface LightboxItem {
	path: string;
	name: string;
	/** "3.4 MB · 2026-10-18" */
	info: string;
	target: PreviewTarget;
	/** Object URL of the row's loaded thumbnail, if any. */
	thumbUrl: () => string | null;
	/** Defaults to "image". Videos get the "Video · duration · info" caption and the playback note; RAWs ("raw", .dng) get "RAW (DNG) · info" and the embedded-preview note. */
	kind?: "image" | "video" | "raw";
	/** Seconds from the poster response (`X-Media-Duration`); null or absent when unknown. */
	durationSeconds?: () => number | null;
	isSelected: () => boolean;
	setSelected: (selected: boolean) => void;
}

interface LightboxHost {
	/** Image rows of the loaded pages, in list order. */
	items: () => readonly LightboxItem[];
	/** `kind: "folders"` mode: file ticks are disabled, so is the lightbox's Selected checkbox. */
	selectionDisabled: () => boolean;
}

type LightboxState = "loading" | "ok" | "error" | "toolarge" | "verror";

const FOCUSABLE = "button:not(:disabled), input:not(:disabled), [href], [tabindex]:not([tabindex='-1'])";

let host: LightboxHost | null = null;
let openPath: string | null = null;
let opener: HTMLElement | null = null;
let controller: AbortController | null = null;
let fullUrl: string | null = null;
let keyBound = false;

function byId<T extends HTMLElement>(id: string): T | null {
	return document.getElementById(id) as T | null;
}
function box(): HTMLElement | null {
	return byId<HTMLElement>("dp-lb");
}

function setState(state: LightboxState): void {
	const lb = box();
	if (lb) {
		lb.dataset.state = state;
	}
}

function setImage(slot: string, url: string | null): HTMLImageElement | null {
	const holder = box()?.querySelector<HTMLElement>(slot) ?? null;
	if (!holder) {
		return null;
	}
	holder.textContent = "";
	if (!url) {
		return null;
	}
	const img = document.createElement("img");
	img.alt = "";
	img.src = url;
	holder.appendChild(img);
	return img;
}

function dropFull(): void {
	if (fullUrl) {
		URL.revokeObjectURL(fullUrl);
		fullUrl = null;
	}
	setImage(".dp-lb-full", null);
}

function abortPending(): void {
	controller?.abort();
	controller = null;
}

function currentIndex(): number {
	const items = host?.items() ?? [];
	return items.findIndex((item) => item.path === openPath);
}

async function loadFull(item: LightboxItem, signal: AbortSignal): Promise<void> {
	try {
		const response = await fetch(buildPreviewUrl("preview", item.target), { signal });
		const outcome = outcomeForStatus(response.status);
		if (signal.aborted) {
			return;
		}
		if (outcome !== "ok") {
			if (item.kind === "video") {
				setState("verror");
				return;
			}
			if (item.kind === "raw" && response.status === 404) {
				// 404 no_preview on a .dng: the RAW-specific sentence. Every other failure keeps the photo text.
				const lb = box();
				if (lb) {
					lb.dataset.rerr = "1";
				}
				setState("error");
				return;
			}
			setState(outcome === "toolarge" && item.thumbUrl() ? "toolarge" : "error");
			return;
		}
		const blob = await response.blob();
		if (signal.aborted) {
			return;
		}
		fullUrl = URL.createObjectURL(blob);
		const img = setImage(".dp-lb-full", fullUrl);
		if (img) {
			img.addEventListener("load", () => {
				if (!signal.aborted) {
					setState("ok");
				}
			});
			img.addEventListener("error", () => {
				if (!signal.aborted) {
					setState(item.kind === "video" ? "verror" : "error");
				}
			});
		}
	} catch {
		if (!signal.aborted) {
			setState(item.kind === "video" ? "verror" : "error");
		}
	}
}

/** Caption under the name: photos show `info`; RAWs "RAW (DNG) · info"; videos get "Video · m:ss · info" (duration omitted when unknown). */
function captionFor(item: LightboxItem): string {
	if (item.kind === "raw") {
		return "RAW (DNG) · " + item.info;
	}
	if (item.kind !== "video") {
		return item.info;
	}
	const seconds = item.durationSeconds?.() ?? null;
	const duration = seconds === null ? "" : formatMediaDuration(seconds);
	return ["Video", duration, item.info].filter((part) => part !== "").join(" · ");
}

function show(item: LightboxItem): void {
	abortPending();
	dropFull();
	openPath = item.path;
	const items = host?.items() ?? [];
	const index = items.findIndex((candidate) => candidate.path === item.path);
	const name = byId<HTMLElement>("dp-lb-name");
	if (name) {
		name.textContent = item.name;
	}
	const info = byId<HTMLElement>("dp-lb-info");
	if (info) {
		info.textContent = captionFor(item);
	}
	const pos = byId<HTMLElement>("dp-lb-pos");
	if (pos) {
		pos.textContent = index >= 0 ? index + 1 + " / " + items.length : "";
	}
	const prev = byId<HTMLButtonElement>("dp-lb-prev");
	if (prev) {
		prev.disabled = stepIndex(index, -1, items.length) === null;
	}
	const next = byId<HTMLButtonElement>("dp-lb-next");
	if (next) {
		next.disabled = stepIndex(index, 1, items.length) === null;
	}
	syncSelection();
	setImage(".dp-lb-blur", item.thumbUrl());
	const lb = box();
	if (lb) {
		lb.dataset.kind = item.kind ?? "image";
		delete lb.dataset.rerr;
		if (item.kind === "video" && !item.thumbUrl()) {
			lb.dataset.poster = "none";
		} else {
			delete lb.dataset.poster;
		}
	}
	setState("loading");
	controller = new AbortController();
	void loadFull(item, controller.signal);
}

/** Mirror the row's tick (and the folders-mode lock) into the lightbox checkbox. */
function syncSelection(): void {
	const sel = byId<HTMLInputElement>("dp-lb-sel");
	const item = host?.items().find((candidate) => candidate.path === openPath);
	if (sel && item) {
		sel.checked = item.isSelected();
		sel.disabled = host?.selectionDisabled() ?? false;
	}
}

function isOpen(): boolean {
	const lb = box();
	return !!lb && !lb.hidden;
}

function step(delta: number): void {
	const items = host?.items() ?? [];
	const target = stepIndex(currentIndex(), delta, items.length);
	const item = target === null ? undefined : items[target];
	if (item) {
		show(item);
	}
}

function open(path: string, from: HTMLElement | null): void {
	const lb = box();
	const item = host?.items().find((candidate) => candidate.path === path);
	if (!lb || !item) {
		return;
	}
	opener = from;
	lb.hidden = false;
	show(item);
	byId<HTMLElement>("dp-lb-close")?.focus();
}

function close(): void {
	const lb = box();
	if (!lb || lb.hidden) {
		return;
	}
	abortPending();
	dropFull();
	setImage(".dp-lb-blur", null);
	lb.hidden = true;
	openPath = null;
	if (opener && document.body.contains(opener)) {
		opener.focus();
	}
	opener = null;
}

function trapFocus(ev: KeyboardEvent): void {
	const lb = box();
	if (!lb) {
		return;
	}
	const focusable = [...lb.querySelectorAll<HTMLElement>(FOCUSABLE)];
	const first = focusable[0];
	const last = focusable[focusable.length - 1];
	if (!first || !last) {
		return;
	}
	const active = document.activeElement;
	if (!lb.contains(active)) {
		ev.preventDefault();
		first.focus();
	} else if (ev.shiftKey && active === first) {
		ev.preventDefault();
		last.focus();
	} else if (!ev.shiftKey && active === last) {
		ev.preventDefault();
		first.focus();
	}
}

function onKeydown(ev: KeyboardEvent): void {
	if (!isOpen()) {
		return;
	}
	switch (ev.key) {
		case "Escape":
			ev.preventDefault();
			ev.stopPropagation();
			close();
			break;
		case "ArrowLeft":
			ev.preventDefault();
			step(-1);
			break;
		case "ArrowRight":
			ev.preventDefault();
			step(1);
			break;
		case "Tab":
			trapFocus(ev);
			break;
		default:
	}
}

/** Wire the lightbox; safe to call again (per-element guard) and re-points `lightboxHost`. */
function bindLightbox(lightboxHost: LightboxHost): void {
	host = lightboxHost;
	if (!keyBound) {
		keyBound = true;
		document.addEventListener("keydown", onKeydown, true);
	}
	const lb = box();
	if (!lb || lb.dataset.dpBound === "1") {
		return;
	}
	lb.dataset.dpBound = "1";
	byId("dp-lb-prev")?.addEventListener("click", () => {
		step(-1);
	});
	byId("dp-lb-next")?.addEventListener("click", () => {
		step(1);
	});
	byId("dp-lb-close")?.addEventListener("click", close);
	lb.querySelector("[data-dp-lb-close]")?.addEventListener("click", close);
	byId<HTMLInputElement>("dp-lb-sel")?.addEventListener("change", (ev: Event) => {
		const item = host?.items().find((candidate) => candidate.path === openPath);
		item?.setSelected((ev.target as HTMLInputElement).checked);
		syncSelection();
	});
}

export type { LightboxHost, LightboxItem };
export {
	bindLightbox,
	close as closeLightbox,
	isOpen as isLightboxOpen,
	open as openLightbox,
	syncSelection as syncLightboxSelection,
};
