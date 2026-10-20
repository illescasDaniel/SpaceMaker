/** Photo previews for the phone picker: URL building, status mapping, a bounded fetch queue and the lazy thumbnail loader. */
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "gif", "heic", "heif"]);
const VIDEO_EXTENSIONS = new Set(["3gp", "avi", "m2ts", "m4v", "mkv", "mov", "mp4", "mts", "webm"]);
/** Concurrent thumbnail requests in flight (the server enforces the same cap per device). */
const MAX_IN_FLIGHT = 4;
/** Start loading a little before the row is on screen. */
const VISIBLE_ROOT_MARGIN = "120px 0px";
function extensionOf(name) {
	const dot = name.lastIndexOf(".");
	return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
}
/** UI hint only; the server decides what it can really decode. */
function isImageName(name) {
	return IMAGE_EXTENSIONS.has(extensionOf(name));
}
function isVideoName(name) {
	return VIDEO_EXTENSIONS.has(extensionOf(name));
}
function buildPreviewUrl(kind, target) {
	const params = new URLSearchParams({
		method: target.method,
		device_id: target.deviceId,
		path: target.path,
		size: String(target.size),
		mtime: String(target.mtime),
	});
	return "/api/device/" + kind + "?" + params.toString();
}
function outcomeForStatus(status) {
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
function retriesOnVisible(outcome) {
	return outcome === "busy" || outcome === "unplugged";
}
/** Index after moving `delta` steps from `current` within `count` items; null at the ends (no wrap). */
function stepIndex(current, delta, count) {
	const next = current + delta;
	return next >= 0 && next < count ? next : null;
}
/** Runs async jobs with at most `limit` in flight; queued jobs wait, cancelled ones never start or get aborted. */
class FetchQueue {
	limit;
	running = 0;
	waiting = [];
	constructor(limit) {
		this.limit = limit;
	}
	get inFlight() {
		return this.running;
	}
	get queued() {
		return this.waiting.length;
	}
	enqueue(job) {
		const controller = new AbortController();
		let started = false;
		let cancelled = false;
		const entry = {
			start: () => {
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
			cancel: () => {
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
	pump() {
		while (this.running < this.limit) {
			const next = this.waiting.shift();
			if (!next) {
				return;
			}
			next.start();
		}
	}
}
function createThumbLoader(root, queue = new FetchQueue(MAX_IN_FLIGHT)) {
	const tiles = new Map();
	let observer = null;
	const setState = (tile, cls) => {
		tile.button.classList.remove("is-loading", "is-failed", "is-toolarge", "is-busy");
		if (cls) {
			tile.button.classList.add(cls);
		}
	};
	const request = (tile) => {
		tile.state = "queued";
		setState(tile, "is-loading");
		tile.handle = queue.enqueue(async (signal) => {
			let outcome;
			let blob = null;
			try {
				const response = await fetch(buildPreviewUrl("thumb", tile.target), { signal });
				outcome = outcomeForStatus(response.status);
				if (outcome === "ok") {
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
	const onIntersect = (entries) => {
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
		register(button, target) {
			tiles.set(button, { button, target, state: "idle", handle: null, objectUrl: null });
			if (typeof IntersectionObserver === "undefined") {
				return;
			}
			if (!observer) {
				observer = new IntersectionObserver(onIntersect, { root, rootMargin: VISIBLE_ROOT_MARGIN });
			}
			observer.observe(button);
		},
		cancelPending() {
			for (const tile of tiles.values()) {
				if (tile.state === "queued") {
					tile.handle?.cancel();
					tile.handle = null;
					tile.state = "idle";
				}
			}
		},
		reset() {
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
		objectUrlFor(button) {
			return tiles.get(button)?.objectUrl ?? null;
		},
	};
}

export {
	buildPreviewUrl,
	createThumbLoader,
	FetchQueue,
	isImageName,
	isVideoName,
	MAX_IN_FLIGHT,
	outcomeForStatus,
	retriesOnVisible,
	stepIndex,
};
