import { apiGet, apiSend } from "./api.ts";
import { encodePathSegments, isDesktopShell } from "./dom.ts";
import { showView } from "./shell.ts";
import { S } from "./state.ts";
import type {
	GalleryExportJob,
	GalleryItem,
	GalleryItemDetail,
	GalleryMetadata,
	ViewId,
	ViewOptions,
} from "./types.ts";

function pathLooksLikeVideo(relativePath: string | undefined | null): boolean {
	return /\.(mp4|mov|mkv|webm|avi|m4v|mts|m2ts)$/i.test(relativePath || "");
}
function prefetchGalleryMedia(relativePath: string | null | undefined): void {
	if (!relativePath) {
		return;
	}
	const thumb = new Image();
	thumb.src = "/thumbs/" + encodePathSegments(relativePath);
	if (!pathLooksLikeVideo(relativePath)) {
		const full = new Image();
		full.src = "/media/" + encodePathSegments(relativePath);
	}
}
function setStageLoading(stage: HTMLElement | null, direction?: "prev" | "next"): void {
	if (!stage) {
		return;
	}
	let outgoing: HTMLElement | null = document.getElementById("gallery-item-media");
	if (!outgoing) {
		outgoing = stage.querySelector(".gallery-item-media.is-incoming") || stage.querySelector(".gallery-item-media");
	}
	if (outgoing && direction) {
		outgoing.id = "";
		outgoing.classList.add("is-outgoing");
		outgoing.classList.remove("is-incoming");
		outgoing.classList.add(direction === "next" ? "slide-out-next" : "slide-out-prev");
		const toRemove = outgoing;
		window.setTimeout(() => {
			if (toRemove.parentNode) {
				toRemove.remove();
			}
		}, 300);
	} else {
		stage.textContent = "";
	}
	const media = document.createElement("div");
	media.className = "gallery-item-media is-incoming";
	media.id = "gallery-item-media";
	if (direction === "next") {
		media.classList.add("slide-in-next-start");
	} else if (direction === "prev") {
		media.classList.add("slide-in-prev-start");
	}
	const thumb = document.createElement("img");
	thumb.className = "gallery-item-thumb";
	thumb.alt = "";
	thumb.setAttribute("aria-hidden", "true");
	thumb.src = "/thumbs/" + encodePathSegments(S.galleryItemPath || "");
	const loading = document.createElement("p");
	loading.className = "gallery-item-loading";
	loading.setAttribute("aria-live", "polite");
	loading.textContent = "• Loading…";
	media.appendChild(thumb);
	media.appendChild(loading);
	// Start full image fetch immediately (do not wait for metadata API). Videos wait on preview_in_browser.
	if (!pathLooksLikeVideo(S.galleryItemPath)) {
		const early = document.createElement("img");
		early.className = "gallery-item-full";
		early.alt = "";
		early.src = "/media/" + encodePathSegments(S.galleryItemPath || "");
		media.appendChild(early);
	}
	stage.appendChild(media);
	if (direction) {
		// Force layout so the slide-in-start transform applies before we clear it,
		// otherwise the browser coalesces both states and skips the animation.
		void media.offsetWidth;
		media.classList.remove("slide-in-next-start", "slide-in-prev-start");
	}
}
function setStageMessage(stage: HTMLElement | null, message: string): void {
	if (!stage) {
		return;
	}
	stage.textContent = "";
	const p = document.createElement("p");
	p.className = "status-line";
	p.textContent = message;
	stage.appendChild(p);
}
function revealGalleryFull(
	media: HTMLElement | null,
	full: HTMLImageElement | HTMLVideoElement | undefined,
	thumb: HTMLElement | null,
): void {
	const loadingEl = media?.querySelector(".gallery-item-loading") || null;
	function hideThumb(e?: Event): void {
		const transEvent = e as TransitionEvent | undefined;
		if (transEvent?.propertyName && transEvent.propertyName !== "opacity") {
			return;
		}
		full?.removeEventListener("transitionend", hideThumb);
		if (thumb) {
			thumb.classList.add("hidden");
		}
	}
	function startFade(): void {
		if (!media?.isConnected || !full) {
			return;
		}
		if (loadingEl) {
			loadingEl.classList.add("hidden");
		}
		full.classList.add("loaded");
		full.addEventListener("transitionend", hideThumb);
		window.setTimeout(() => {
			hideThumb();
		}, 350);
	}
	function afterPainted(): void {
		if (full instanceof HTMLImageElement && typeof full.decode === "function") {
			full.decode().then(startFade, startFade);
		} else {
			startFade();
		}
	}
	requestAnimationFrame(() => {
		requestAnimationFrame(afterPainted);
	});
}
function renderGalleryItemStage(stage: HTMLElement | null, payload: GalleryItemDetail, meta: GalleryMetadata): void {
	if (!stage) {
		return;
	}
	const media =
		stage.querySelector<HTMLElement>("#gallery-item-media") ||
		stage.querySelector<HTMLElement>(".gallery-item-media.is-incoming");
	if (!media) {
		return;
	}
	const thumb = media.querySelector<HTMLElement>(".gallery-item-thumb");
	const loadingEl = media.querySelector<HTMLElement>(".gallery-item-loading");
	const mediaUrl = "/media/" + encodePathSegments(payload.relative_path);
	const label = meta.filename || payload.relative_path;
	const earlyFull = media.querySelector<HTMLElement>(".gallery-item-full");
	let full: HTMLImageElement | HTMLVideoElement | undefined;
	function reveal(): void {
		revealGalleryFull(media, full, thumb);
	}
	if (payload.kind === "video") {
		if (earlyFull) {
			earlyFull.remove();
		}
		if (payload.preview_in_browser) {
			const video = document.createElement("video");
			video.className = "gallery-item-full";
			video.controls = true;
			video.preload = "metadata";
			video.setAttribute("aria-label", label);
			full = video;
			video.addEventListener("loadeddata", reveal, { once: true });
			video.src = mediaUrl;
			media.appendChild(video);
		} else {
			const noPreview = document.createElement("p");
			noPreview.className = "status-line gallery-no-preview";
			noPreview.textContent =
				"No in-browser preview for this codec (e.g. HEVC). Use Open on desktop or download the file.";
			media.appendChild(noPreview);
			if (loadingEl) {
				loadingEl.classList.add("hidden");
			}
		}
		return;
	}
	if (earlyFull instanceof HTMLImageElement) {
		full = earlyFull;
		full.alt = label;
		if (full.complete && full.naturalWidth > 0) {
			reveal();
		} else {
			full.addEventListener("load", reveal, { once: true });
		}
		return;
	}
	if (earlyFull) {
		earlyFull.remove();
	}
	const img = document.createElement("img");
	img.className = "gallery-item-full";
	img.alt = label;
	img.addEventListener("load", reveal, { once: true });
	img.src = mediaUrl;
	full = img;
	media.appendChild(img);
}
function galleryItemPathFromLocation(): string {
	const prefix = "/gallery/item/";
	if (location.pathname.indexOf(prefix) !== 0) {
		return "";
	}
	return decodeURIComponent(location.pathname.slice(prefix.length));
}
function closeGalleryPhonePopup(): void {
	const popup = document.getElementById("gallery-phone-popup");
	const fab = document.getElementById("btn-gallery-phone-help");
	if (popup) {
		popup.classList.add("panel-hidden");
	}
	if (fab) {
		fab.setAttribute("aria-expanded", "false");
	}
}
function toggleGalleryPhonePopup(): void {
	const popup = document.getElementById("gallery-phone-popup");
	const fab = document.getElementById("btn-gallery-phone-help");
	if (!popup || !fab) {
		return;
	}
	const open = popup.classList.contains("panel-hidden");
	popup.classList.toggle("panel-hidden", !open);
	fab.setAttribute("aria-expanded", open ? "true" : "false");
}
function syncGalleryPhoneHelpVisibility(resolvedViewId: ViewId): void {
	const fab = document.getElementById("btn-gallery-phone-help");
	if (!fab || !isDesktopShell()) {
		return;
	}
	const onGallery = resolvedViewId === "gallery" || resolvedViewId === "gallery-item";
	fab.hidden = !onGallery;
	if (!onGallery) {
		closeGalleryPhonePopup();
	}
}
function fetchGalleryNeighbor(path: string, direction: "prev" | "next"): Promise<string | null> {
	return apiSend<{ relative_path: string | null }>(
		"GET",
		"/api/gallery/item/neighbor?path=" + encodeURIComponent(path) + "&direction=" + direction,
	)
		.then((payload) => payload.relative_path || null)
		.catch(() => null);
}
function refreshGalleryItemNeighbors(path: string): Promise<void> {
	return Promise.all([fetchGalleryNeighbor(path, "prev"), fetchGalleryNeighbor(path, "next")]).then((results) => {
		if (path !== S.galleryItemPath) {
			return; // a newer navigation started while these were in flight
		}
		S.galleryItemNeighbors = { prev: results[0] ?? null, next: results[1] ?? null };
		updateGalleryItemNav();
		prefetchGalleryMedia(results[0]);
		prefetchGalleryMedia(results[1]);
	});
}
function updateGalleryItemNav(): void {
	const prevBtn = document.getElementById("btn-gallery-item-prev");
	const nextBtn = document.getElementById("btn-gallery-item-next");
	if (!(prevBtn instanceof HTMLButtonElement) || !(nextBtn instanceof HTMLButtonElement)) {
		return;
	}
	prevBtn.disabled = !S.galleryItemNeighbors.prev;
	nextBtn.disabled = !S.galleryItemNeighbors.next;
}
function shiftGalleryItem(delta: number): void {
	const direction: "prev" | "next" = delta < 0 ? "prev" : "next";
	const target = delta < 0 ? S.galleryItemNeighbors.prev : S.galleryItemNeighbors.next;
	if (!target) {
		return;
	}
	// No blank delay — setStageLoading keeps outgoing media until the incoming thumb covers it.
	S.galleryItemPath = target;
	S.galleryItemNeighbors = { prev: null, next: null };
	updateGalleryItemNav();
	const itemPath = "/gallery/item/" + encodePathSegments(S.galleryItemPath);
	if (location.pathname !== itemPath) {
		history.pushState({ view: "gallery-item", path: S.galleryItemPath }, "", itemPath);
	}
	loadGalleryItemDetail(direction);
	refreshGalleryItemNeighbors(S.galleryItemPath);
}
function showGalleryItem(relativePath: string, options?: ViewOptions): void {
	S.galleryItemPath = relativePath;
	S.galleryItemNeighbors = { prev: null, next: null };
	updateGalleryItemNav();
	showView("gallery-item", options || {});
	loadGalleryItemDetail();
	refreshGalleryItemNeighbors(relativePath);
}
function appendThumbCell(grid: Element, item: GalleryItem): void {
	const cell = document.createElement("button");
	const img = document.createElement("img");
	cell.type = "button";
	cell.className = "thumb thumb-link";
	img.src = "/thumbs/" + encodePathSegments(item.relative_path);
	img.alt = item.relative_path;
	img.loading = "lazy";
	cell.appendChild(img);
	if (item.kind === "video") {
		const badge = document.createElement("span");
		badge.className = "thumb-badge";
		badge.textContent = "Video";
		cell.appendChild(badge);
	}
	cell.addEventListener("click", () => {
		showGalleryItem(item.relative_path);
	});
	grid.appendChild(cell);
}
function formatFileSize(bytes: number | null | undefined): string {
	if (!bytes && bytes !== 0) {
		return "—";
	}
	if (bytes < 1024) {
		return bytes + " B";
	}
	if (bytes < 1024 * 1024) {
		return (bytes / 1024).toFixed(1) + " KB";
	}
	return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}
function formatDuration(seconds: number | null | undefined): string {
	if (seconds === null || seconds === undefined) {
		return "—";
	}
	const total = Math.round(seconds);
	const mins = Math.floor(total / 60);
	const secs = total % 60;
	if (mins > 0) {
		return mins + "m " + secs + "s";
	}
	return secs + "s";
}
function formatCaptured(iso: string | null | undefined): string {
	if (!iso) {
		return "—";
	}
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) {
		return iso;
	}
	return d.toLocaleString();
}
function setGalleryExportProgress(percent: number, label?: string): void {
	const bar = document.getElementById("gallery-export-progress");
	const fill = document.getElementById("gallery-export-fill");
	const labelEl = document.getElementById("gallery-export-label");
	if (labelEl && label) {
		labelEl.textContent = label;
	}
	if (bar) {
		bar.setAttribute("aria-valuenow", String(percent));
	}
	if (fill) {
		fill.style.width = String(percent) + "%";
	}
}
function hideGalleryExportAlert(): void {
	const alertEl = document.getElementById("gallery-export-alert");
	const err = document.getElementById("gallery-export-error");
	if (alertEl) {
		alertEl.hidden = true;
	}
	if (err) {
		err.hidden = true;
		err.textContent = "";
	}
	setGalleryExportProgress(0, "Preparing download…");
}
function triggerFileDownload(url: string): void {
	const a = document.createElement("a");
	a.href = url;
	a.rel = "noopener";
	document.body.appendChild(a);
	a.click();
	a.remove();
}
let lastDeliveredExportUrl = "";
function deliverFriendlyExport(downloadUrl: string): void {
	// WS push (desktop) and HTTP poll (phones) can both report "done"; download once.
	if (downloadUrl === lastDeliveredExportUrl) {
		return;
	}
	lastDeliveredExportUrl = downloadUrl;
	setGalleryExportProgress(100, "Download starting…");
	triggerFileDownload(downloadUrl);
	setTimeout(hideGalleryExportAlert, 1500);
}
function applyGalleryExport(exp: GalleryExportJob | null | undefined): void {
	if (!exp || exp.relative_path !== S.galleryItemPath) {
		return;
	}
	const alertEl = document.getElementById("gallery-export-alert");
	const err = document.getElementById("gallery-export-error");
	if (alertEl) {
		alertEl.hidden = false;
	}
	if (exp.phase === "error") {
		setGalleryExportProgress(exp.percent || 0, "Export failed");
		if (err) {
			err.hidden = false;
			err.textContent = exp.error || "Export failed.";
		}
		return;
	}
	if (exp.phase === "running") {
		setGalleryExportProgress(exp.percent || 0, "Preparing download…");
		return;
	}
	if (exp.phase === "done") {
		if (exp.download_url) {
			deliverFriendlyExport(exp.download_url);
		} else {
			setTimeout(hideGalleryExportAlert, 1500);
		}
	}
}
const EXPORT_POLL_MS = 700;
let exportPollToken = 0;
function pollGalleryExport(jobId: string, relativePath: string, token: number): void {
	setTimeout(() => {
		if (token !== exportPollToken || S.galleryItemPath !== relativePath) {
			return;
		}
		apiGet<GalleryExportJob>("/api/gallery/export/" + encodeURIComponent(jobId))
			.then((job) => {
				if (token !== exportPollToken) {
					return;
				}
				applyGalleryExport(job);
				if (job.phase === "running") {
					pollGalleryExport(jobId, relativePath, token);
				}
			})
			.catch((pollErr: unknown) => {
				if (token !== exportPollToken) {
					return;
				}
				applyGalleryExport({
					job_id: jobId,
					relative_path: relativePath,
					format: "",
					phase: "error",
					percent: 0,
					download_url: "",
					error: pollErr instanceof Error ? pollErr.message : "Export failed.",
					skipped_encode: false,
				});
			});
	}, EXPORT_POLL_MS);
}
function startFriendlyExport(): void {
	exportPollToken += 1;
	const token = exportPollToken;
	const fmt = S.galleryItemKind === "video" ? "h264_aac" : "jpeg";
	const alertEl = document.getElementById("gallery-export-alert");
	hideGalleryExportAlert();
	setGalleryExportProgress(0, "Preparing download…");
	if (alertEl) {
		alertEl.hidden = false;
	}
	apiSend<GalleryExportJob>("POST", "/api/gallery/export", { relative_path: S.galleryItemPath, format: fmt })
		.then((job) => {
			if (token !== exportPollToken) {
				return;
			}
			applyGalleryExport(job);
			if (job.phase === "running" && job.job_id) {
				pollGalleryExport(job.job_id, job.relative_path, token);
			}
		})
		.catch((exportErr: unknown) => {
			const message = exportErr instanceof Error ? exportErr.message : "Export failed.";
			applyGalleryExport({
				job_id: "",
				relative_path: S.galleryItemPath || "",
				format: fmt,
				phase: "error",
				percent: 0,
				download_url: "",
				error: message || "Export failed.",
				skipped_encode: false,
			});
		});
}
function loadGalleryItemDetail(direction?: "prev" | "next"): void {
	const stage = document.getElementById("gallery-item-stage");
	const title = document.getElementById("gallery-item-title");
	const metaHost = document.getElementById("gallery-item-meta");
	const friendly = document.getElementById("btn-gallery-friendly");
	if (!stage || !S.galleryItemPath) {
		return;
	}
	hideGalleryExportAlert();
	setStageLoading(stage, direction);
	updateGalleryItemNav();
	// Rapid prev/next: only the response for the item currently shown may render.
	const requestedPath = S.galleryItemPath;
	apiSend<GalleryItemDetail>("GET", "/api/gallery/item?path=" + encodeURIComponent(requestedPath))
		.then((payload) => {
			if (S.galleryItemPath !== requestedPath) {
				return;
			}
			const meta = payload.metadata;
			S.galleryItemKind = payload.kind === "video" ? "video" : "image";
			if (title) {
				title.textContent = meta.filename || payload.relative_path;
			}
			renderGalleryItemStage(stage, payload, meta);
			if (friendly) {
				if (payload.kind === "video") {
					const mp4Ok = S.state?.video_friendly_export_available;
					friendly.hidden = !mp4Ok;
					friendly.textContent = "Download as MP4";
				} else {
					friendly.hidden = false;
					friendly.textContent = "Download as JPEG";
				}
			}
			if (metaHost) {
				const rows: [string, string][] = [
					["Captured", formatCaptured(meta.captured_at || payload.captured_at)],
					[
						"Camera",
						meta.camera_make || meta.camera_model
							? [meta.camera_make, meta.camera_model].filter(Boolean).join(" · ")
							: "—",
					],
					["Dimensions", meta.width && meta.height ? meta.width + " × " + meta.height : "—"],
					["File size", formatFileSize(meta.file_size_bytes)],
				];
				if (payload.absolute_path) {
					// Empty for LAN phones: the host path is only shared with the desktop app.
					rows.unshift(["On disk", payload.absolute_path]);
				}
				if (payload.kind === "video") {
					rows.push(["Duration", formatDuration(meta.duration_seconds)]);
				}
				if (meta.gps) {
					rows.push(["Location", meta.gps]);
				}
				metaHost.innerHTML = "";
				rows.forEach((row) => {
					const dt = document.createElement("dt");
					const dd = document.createElement("dd");
					dt.textContent = row[0];
					dd.textContent = row[1];
					if (row[0] === "On disk") {
						dt.className = "gallery-disk-path";
						dd.className = "gallery-disk-path";
					}
					metaHost.appendChild(dt);
					metaHost.appendChild(dd);
				});
			}
			updateGalleryItemNav();
		})
		.catch(() => {
			if (S.galleryItemPath !== requestedPath) {
				return;
			}
			setStageMessage(stage, "Could not load this item.");
			updateGalleryItemNav();
		});
}

export {
	appendThumbCell,
	applyGalleryExport,
	closeGalleryPhonePopup,
	deliverFriendlyExport,
	fetchGalleryNeighbor,
	formatCaptured,
	formatDuration,
	formatFileSize,
	galleryItemPathFromLocation,
	hideGalleryExportAlert,
	loadGalleryItemDetail,
	pathLooksLikeVideo,
	prefetchGalleryMedia,
	refreshGalleryItemNeighbors,
	renderGalleryItemStage,
	revealGalleryFull,
	setGalleryExportProgress,
	setStageLoading,
	setStageMessage,
	shiftGalleryItem,
	showGalleryItem,
	startFriendlyExport,
	syncGalleryPhoneHelpVisibility,
	toggleGalleryPhonePopup,
	triggerFileDownload,
	updateGalleryItemNav,
};
