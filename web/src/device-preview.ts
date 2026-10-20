/** Photo previews for the phone picker: URL building, status mapping, a bounded fetch queue and the lazy thumbnail loader. */

const IMAGE_EXTENSIONS: ReadonlySet<string> = new Set(["jpg", "jpeg", "png", "webp", "gif", "heic", "heif"]);
const VIDEO_EXTENSIONS: ReadonlySet<string> = new Set([
	"3gp",
	"avi",
	"m2ts",
	"m4v",
	"mkv",
	"mov",
	"mp4",
	"mts",
	"webm",
]);

/** Videos that get a poster frame (the rest keep the 🎞 icon). */
const POSTER_EXTENSIONS: ReadonlySet<string> = new Set(["3gp", "m4v", "mkv", "mov", "mp4", "webm"]);
const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;

/** Concurrent thumbnail requests in flight (the server enforces the same cap per device). */
const MAX_IN_FLIGHT = 4;
/** Start loading a little before the row is on screen. */
const VISIBLE_ROOT_MARGIN = "120px 0px";

type PreviewKind = "thumb" | "preview";

interface PreviewTarget {
	method: "adb" | "afc";
	deviceId: string;
	/** Storage-relative path, as sent to `/api/device/list`. */
	path: string;
	size: number;
	mtime: number;
}

/** What a finished request means for a tile. */
type PreviewOutcome = "ok" | "busy" | "toolarge" | "unplugged" | "failed";

function extensionOf(name: string): string {
	const dot = name.lastIndexOf(".");
	return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
}
/** UI hint only; the server decides what it can really decode. */
function isImageName(name: string): boolean {
	return IMAGE_EXTENSIONS.has(extensionOf(name));
}
function isVideoName(name: string): boolean {
	return VIDEO_EXTENSIONS.has(extensionOf(name));
}

/** True for the video extensions that get a poster (mp4, mov, m4v, 3gp, mkv, webm; case-insensitive). */
function isPreviewableVideo(name: string): boolean {
	return POSTER_EXTENSIONS.has(extensionOf(name));
}

/** `m:ss` (`0:42`, `12:07`), `h:mm:ss` from one hour; rounds down; "" for NaN or negative. */
function formatMediaDuration(seconds: number): string {
	if (!Number.isFinite(seconds) || seconds < 0) {
		return "";
	}
	const total = Math.floor(seconds);
	const hours = Math.floor(total / SECONDS_PER_HOUR);
	const minutes = Math.floor((total % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
	const secs = String(total % SECONDS_PER_MINUTE).padStart(2, "0");
	if (hours > 0) {
		return hours + ":" + String(minutes).padStart(2, "0") + ":" + secs;
	}
	return minutes + ":" + secs;
}

/** Decimal seconds from the `X-Media-Duration` header; null when missing or not a finite non-negative number. */
function parseMediaDuration(header: string | null): number | null {
	if (header === null || header.trim() === "") {
		return null;
	}
	const value = Number(header);
	return Number.isFinite(value) && value >= 0 ? value : null;
}

function buildPreviewUrl(kind: PreviewKind, target: PreviewTarget): string {
	const params = new URLSearchParams({
		method: target.method,
		device_id: target.deviceId,
		path: target.path,
		size: String(target.size),
		mtime: String(target.mtime),
	});
	return "/api/device/" + kind + "?" + params.toString();
}

function outcomeForStatus(status: number): PreviewOutcome {
	if (status >= 200 && status < 300) {
		return "ok";
	}
	switch (status) {
		case 409:
			return "busy";
		case 413:
			return "toolarge";
		case 503:
			return "unplugged";
		default:
			return "failed";
	}
}

/** Only these outcomes are asked for again the next time the row becomes visible. */
function retriesOnVisible(outcome: PreviewOutcome): boolean {
	return outcome === "busy" || outcome === "unplugged";
}

/** Index after moving `delta` steps from `current` within `count` items; null at the ends (no wrap). */
function stepIndex(current: number, delta: number, count: number): number | null {
	const next = current + delta;
	return next >= 0 && next < count ? next : null;
}

interface QueueHandle {
	cancel: () => void;
}

/** Runs async jobs with at most `limit` in flight; queued jobs wait, cancelled ones never start or get aborted. */
class FetchQueue {
	private readonly limit: number;
	private running = 0;
	private readonly waiting: Array<{ start: () => void }> = [];

	constructor(limit: number) {
		this.limit = limit;
	}

	get inFlight(): number {
		return this.running;
	}

	get queued(): number {
		return this.waiting.length;
	}

	enqueue(job: (signal: AbortSignal) => Promise<void>): QueueHandle {
		const controller = new AbortController();
		let started = false;
		let cancelled = false;
		const entry = {
			start: (): void => {
				started = true;
				this.running += 1;
				void job(controller.signal)
					.catch(() => undefined)
					.finally(() => {
						this.running -= 1;
						this.pump();
					});
			},
		};
		this.waiting.push(entry);
		this.pump();
		return {
			cancel: (): void => {
				if (cancelled) {
					return;
				}
				cancelled = true;
				if (started) {
					controller.abort();
					return;
				}
				const at = this.waiting.indexOf(entry);
				if (at >= 0) {
					this.waiting.splice(at, 1);
				}
			},
		};
	}

	private pump(): void {
		while (this.running < this.limit) {
			const next = this.waiting.shift();
			if (!next) {
				return;
			}
			next.start();
		}
	}
}

type TileState = "idle" | "queued" | "loaded" | "settled";

interface Tile {
	button: HTMLButtonElement;
	target: PreviewTarget;
	state: TileState;
	handle: QueueHandle | null;
	objectUrl: string | null;
	duration: number | null;
	onPoster: ((duration: number | null) => void) | null;
}

interface ThumbLoader {
	/** Start watching a thumbnail button; it loads once it scrolls into view. `onPoster` fires after a poster loads. */
	register: (button: HTMLButtonElement, target: PreviewTarget, onPoster?: (duration: number | null) => void) => void;
	/** Abort queued and running requests but keep what is already loaded (rows still on screen). */
	cancelPending: () => void;
	/** Abort everything, revoke every object URL and forget all tiles (rows are being removed). */
	reset: () => void;
	/** Object URL of an already loaded thumbnail, if any. */
	objectUrlFor: (button: HTMLButtonElement) => string | null;
	/** Duration in seconds from the `X-Media-Duration` header of a loaded video poster; null when unknown. */
	durationFor: (button: HTMLButtonElement) => number | null;
}

function createThumbLoader(root: HTMLElement | null, queue: FetchQueue = new FetchQueue(MAX_IN_FLIGHT)): ThumbLoader {
	const tiles = new Map<Element, Tile>();
	let observer: IntersectionObserver | null = null;

	const setState = (tile: Tile, cls: string | null): void => {
		tile.button.classList.remove("is-loading", "is-failed", "is-toolarge", "is-busy");
		if (cls) {
			tile.button.classList.add(cls);
		}
	};

	const applyDuration = (button: HTMLButtonElement, duration: number | null): void => {
		const badge = button.querySelector(".dp-thumb-dur");
		if (!badge) {
			return;
		}
		const text = duration === null ? "" : formatMediaDuration(duration);
		badge.textContent = text;
		const label = button.getAttribute("aria-label");
		if (label) {
			button.setAttribute(
				"aria-label",
				label.replace(/ \(video[^)]*\)$/, text ? " (video, " + text + ")" : " (video)"),
			);
		}
	};

	const request = (tile: Tile): void => {
		tile.state = "queued";
		setState(tile, "is-loading");
		tile.handle = queue.enqueue(async (signal: AbortSignal): Promise<void> => {
			let outcome: PreviewOutcome;
			let blob: Blob | null = null;
			let duration: number | null = null;
			try {
				const response = await fetch(buildPreviewUrl("thumb", tile.target), { signal });
				outcome = outcomeForStatus(response.status);
				if (outcome === "ok") {
					duration = parseMediaDuration(response.headers.get("X-Media-Duration"));
					blob = await response.blob();
				}
			} catch {
				if (signal.aborted) {
					return;
				}
				outcome = "unplugged";
			}
			if (signal.aborted || !tiles.has(tile.button)) {
				return;
			}
			tile.handle = null;
			if (blob) {
				tile.duration = duration;
				applyDuration(tile.button, duration);
				tile.onPoster?.(duration);
				const url = URL.createObjectURL(blob);
				tile.objectUrl = url;
				const img = document.createElement("img");
				img.className = "dp-thumb-img";
				img.alt = "";
				img.decoding = "async";
				img.src = url;
				tile.button.querySelector(".dp-thumb-img")?.remove();
				tile.button.insertBefore(img, tile.button.firstChild);
				tile.state = "loaded";
				setState(tile, null);
				return;
			}
			tile.state = retriesOnVisible(outcome) ? "idle" : "settled";
			setState(tile, outcome === "busy" ? "is-busy" : outcome === "toolarge" ? "is-toolarge" : "is-failed");
		});
	};

	const onIntersect = (entries: ReadonlyArray<{ target: Element; isIntersecting: boolean }>): void => {
		for (const entry of entries) {
			const tile = tiles.get(entry.target);
			if (!tile) {
				continue;
			}
			if (entry.isIntersecting) {
				if (tile.state === "idle") {
					request(tile);
				}
			} else if (tile.state === "queued") {
				tile.handle?.cancel();
				tile.handle = null;
				tile.state = "idle";
				setState(tile, "is-loading");
			}
		}
	};

	return {
		register(button: HTMLButtonElement, target: PreviewTarget, onPoster?: (duration: number | null) => void): void {
			tiles.set(button, {
				button,
				target,
				state: "idle",
				handle: null,
				objectUrl: null,
				duration: null,
				onPoster: onPoster ?? null,
			});
			if (typeof IntersectionObserver === "undefined") {
				return;
			}
			if (!observer) {
				observer = new IntersectionObserver(onIntersect, { root, rootMargin: VISIBLE_ROOT_MARGIN });
			}
			observer.observe(button);
		},
		cancelPending(): void {
			for (const tile of tiles.values()) {
				if (tile.state === "queued") {
					tile.handle?.cancel();
					tile.handle = null;
					tile.state = "idle";
				}
			}
		},
		reset(): void {
			for (const tile of tiles.values()) {
				tile.handle?.cancel();
				if (tile.objectUrl) {
					URL.revokeObjectURL(tile.objectUrl);
				}
			}
			tiles.clear();
			observer?.disconnect();
			observer = null;
		},
		objectUrlFor(button: HTMLButtonElement): string | null {
			return tiles.get(button)?.objectUrl ?? null;
		},
		durationFor(button: HTMLButtonElement): number | null {
			return tiles.get(button)?.duration ?? null;
		},
	};
}

export type { PreviewKind, PreviewOutcome, PreviewTarget, QueueHandle, ThumbLoader };
export {
	buildPreviewUrl,
	createThumbLoader,
	FetchQueue,
	formatMediaDuration,
	isImageName,
	isPreviewableVideo,
	isVideoName,
	MAX_IN_FLIGHT,
	outcomeForStatus,
	retriesOnVisible,
	stepIndex,
};
