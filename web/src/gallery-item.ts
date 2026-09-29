// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function pathLooksLikeVideo(relativePath) {
	return /\.(mp4|mov|mkv|webm|avi|m4v|mts|m2ts)$/i.test(relativePath || "");
}
function prefetchGalleryMedia(relativePath) {
	if (!relativePath) {
		return;
	}
	var thumb = new Image();
	var full;
	thumb.src = "/thumbs/" + encodeURI(relativePath);
	if (!pathLooksLikeVideo(relativePath)) {
		full = new Image();
		full.src = "/media/" + encodeURI(relativePath);
	}
}
function setStageLoading(stage, direction) {
	if (!stage) {
		return;
	}
	var outgoing = document.getElementById("gallery-item-media");
	var media;
	var thumb;
	var loading;
	var early;
	if (!outgoing) {
		outgoing = stage.querySelector(".gallery-item-media.is-incoming") || stage.querySelector(".gallery-item-media");
	}
	if (outgoing && direction) {
		outgoing.id = "";
		outgoing.classList.add("is-outgoing");
		outgoing.classList.remove("is-incoming");
		outgoing.classList.add(direction === "next" ? "slide-out-next" : "slide-out-prev");
		window.setTimeout(function () {
			if (outgoing.parentNode) {
				outgoing.remove();
			}
		}, 300);
	} else {
		stage.textContent = "";
		outgoing = null;
	}
	media = document.createElement("div");
	media.className = "gallery-item-media is-incoming";
	media.id = "gallery-item-media";
	if (direction === "next") {
		media.classList.add("slide-in-next-start");
	} else if (direction === "prev") {
		media.classList.add("slide-in-prev-start");
	}
	thumb = document.createElement("img");
	thumb.className = "gallery-item-thumb";
	thumb.alt = "";
	thumb.setAttribute("aria-hidden", "true");
	thumb.src = "/thumbs/" + encodeURI(S.galleryItemPath);
	loading = document.createElement("p");
	loading.className = "gallery-item-loading";
	loading.setAttribute("aria-live", "polite");
	loading.textContent = "• Loading…";
	media.appendChild(thumb);
	media.appendChild(loading);
	// Start full image fetch immediately (do not wait for metadata API). Videos wait on preview_in_browser.
	if (!pathLooksLikeVideo(S.galleryItemPath)) {
		early = document.createElement("img");
		early.className = "gallery-item-full";
		early.alt = "";
		early.src = "/media/" + encodeURI(S.galleryItemPath);
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
function setStageMessage(stage, message) {
	if (!stage) {
		return;
	}
	stage.textContent = "";
	var p = document.createElement("p");
	p.className = "status-line";
	p.textContent = message;
	stage.appendChild(p);
}
function revealGalleryFull(media, full, thumb) {
	var loadingEl = media?.querySelector(".gallery-item-loading") || null;
	function startFade() {
		if (!media?.isConnected || !full) {
			return;
		}
		if (loadingEl) {
			loadingEl.classList.add("hidden");
		}
		full.classList.add("loaded");
		function hideThumb(e) {
			if (e?.propertyName && e.propertyName !== "opacity") {
				return;
			}
			full.removeEventListener("transitionend", hideThumb);
			if (thumb) {
				thumb.classList.add("hidden");
			}
		}
		full.addEventListener("transitionend", hideThumb);
		window.setTimeout(function () {
			hideThumb();
		}, 350);
	}
	function afterPainted() {
		if (full.tagName === "IMG" && typeof full.decode === "function") {
			full.decode().then(startFade, startFade);
		} else {
			startFade();
		}
	}
	requestAnimationFrame(function () {
		requestAnimationFrame(afterPainted);
	});
}
function renderGalleryItemStage(stage, payload, meta) {
	if (!stage) {
		return;
	}
	var media = stage.querySelector("#gallery-item-media") || stage.querySelector(".gallery-item-media.is-incoming");
	if (!media) {
		return;
	}
	var thumb = media.querySelector(".gallery-item-thumb");
	var loadingEl = media.querySelector(".gallery-item-loading");
	var mediaUrl = "/media/" + encodeURI(payload.relative_path);
	var label = meta.filename || payload.relative_path;
	var earlyFull = media.querySelector(".gallery-item-full");
	var video;
	var noPreview;
	var full;
	function reveal() {
		revealGalleryFull(media, full, thumb);
	}
	if (payload.kind === "video") {
		if (earlyFull) {
			earlyFull.remove();
		}
		if (payload.preview_in_browser) {
			video = document.createElement("video");
			video.className = "gallery-item-full";
			video.controls = true;
			video.preload = "metadata";
			video.setAttribute("aria-label", label);
			full = video;
			video.addEventListener("loadeddata", reveal, { once: true });
			video.src = mediaUrl;
			media.appendChild(video);
		} else {
			noPreview = document.createElement("p");
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
	if (earlyFull && earlyFull.tagName === "IMG") {
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
	full = document.createElement("img");
	full.className = "gallery-item-full";
	full.alt = label;
	full.addEventListener("load", reveal, { once: true });
	full.src = mediaUrl;
	media.appendChild(full);
}
function galleryItemPathFromLocation() {
	var prefix = "/gallery/item/";
	if (location.pathname.indexOf(prefix) !== 0) {
		return "";
	}
	return decodeURIComponent(location.pathname.slice(prefix.length));
}
function closeGalleryPhonePopup() {
	var popup = document.getElementById("gallery-phone-popup");
	var fab = document.getElementById("btn-gallery-phone-help");
	if (popup) {
		popup.classList.add("panel-hidden");
	}
	if (fab) {
		fab.setAttribute("aria-expanded", "false");
	}
}
function toggleGalleryPhonePopup() {
	var popup = document.getElementById("gallery-phone-popup");
	var fab = document.getElementById("btn-gallery-phone-help");
	if (!popup || !fab) {
		return;
	}
	var open = popup.classList.contains("panel-hidden");
	popup.classList.toggle("panel-hidden", !open);
	fab.setAttribute("aria-expanded", open ? "true" : "false");
}
function syncGalleryPhoneHelpVisibility(resolvedViewId) {
	var fab = document.getElementById("btn-gallery-phone-help");
	if (!fab || !R.isDesktopShell()) {
		return;
	}
	var onGallery = resolvedViewId === "gallery" || resolvedViewId === "gallery-item";
	fab.hidden = !onGallery;
	if (!onGallery) {
		closeGalleryPhonePopup();
	}
}
function fetchGalleryNeighbor(path, direction) {
	return R.api("GET", "/api/gallery/item/neighbor?path=" + encodeURIComponent(path) + "&direction=" + direction)
		.then(function (payload) {
			return payload.relative_path || null;
		})
		.catch(function () {
			return null;
		});
}
function refreshGalleryItemNeighbors(path) {
	return Promise.all([fetchGalleryNeighbor(path, "prev"), fetchGalleryNeighbor(path, "next")]).then(function (results) {
		if (path !== S.galleryItemPath) {
			return; // a newer navigation started while these were in flight
		}
		S.galleryItemNeighbors = { prev: results[0], next: results[1] };
		updateGalleryItemNav();
		prefetchGalleryMedia(results[0]);
		prefetchGalleryMedia(results[1]);
	});
}
function updateGalleryItemNav() {
	var prevBtn = document.getElementById("btn-gallery-item-prev");
	var nextBtn = document.getElementById("btn-gallery-item-next");
	if (!prevBtn || !nextBtn) {
		return;
	}
	prevBtn.disabled = !S.galleryItemNeighbors.prev;
	nextBtn.disabled = !S.galleryItemNeighbors.next;
}
function shiftGalleryItem(delta) {
	var direction = delta < 0 ? "prev" : "next";
	var target = delta < 0 ? S.galleryItemNeighbors.prev : S.galleryItemNeighbors.next;
	if (!target) {
		return;
	}
	// No blank delay — setStageLoading keeps outgoing media until the incoming thumb covers it.
	S.galleryItemPath = target;
	S.galleryItemNeighbors = { prev: null, next: null };
	updateGalleryItemNav();
	var itemPath = "/gallery/item/" + encodeURI(S.galleryItemPath);
	if (location.pathname !== itemPath) {
		history.pushState({ view: "gallery-item", path: S.galleryItemPath }, "", itemPath);
	}
	loadGalleryItemDetail(direction);
	refreshGalleryItemNeighbors(S.galleryItemPath);
}
function showGalleryItem(relativePath, options) {
	S.galleryItemPath = relativePath;
	S.galleryItemNeighbors = { prev: null, next: null };
	updateGalleryItemNav();
	R.showView("gallery-item", options || {});
	loadGalleryItemDetail();
	refreshGalleryItemNeighbors(relativePath);
}
function appendThumbCell(grid, item) {
	var cell = document.createElement("button");
	var img = document.createElement("img");
	var badge;
	cell.type = "button";
	cell.className = "thumb thumb-link";
	img.src = "/thumbs/" + encodeURI(item.relative_path);
	img.alt = item.relative_path;
	img.loading = "lazy";
	cell.appendChild(img);
	if (item.kind === "video") {
		badge = document.createElement("span");
		badge.className = "thumb-badge";
		badge.textContent = "Video";
		cell.appendChild(badge);
	}
	cell.addEventListener("click", function () {
		showGalleryItem(item.relative_path);
	});
	grid.appendChild(cell);
}
function formatFileSize(bytes) {
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
function formatDuration(seconds) {
	if (seconds === null || seconds === undefined) {
		return "—";
	}
	var total = Math.round(seconds);
	var mins = Math.floor(total / 60);
	var secs = total % 60;
	if (mins > 0) {
		return mins + "m " + secs + "s";
	}
	return secs + "s";
}
function formatCaptured(iso) {
	if (!iso) {
		return "—";
	}
	var d = new Date(iso);
	if (Number.isNaN(d.getTime())) {
		return iso;
	}
	return d.toLocaleString();
}
function setGalleryExportProgress(percent, label) {
	var bar = document.getElementById("gallery-export-progress");
	var fill = document.getElementById("gallery-export-fill");
	var labelEl = document.getElementById("gallery-export-label");
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
function hideGalleryExportAlert() {
	var alertEl = document.getElementById("gallery-export-alert");
	var err = document.getElementById("gallery-export-error");
	if (alertEl) {
		alertEl.hidden = true;
	}
	if (err) {
		err.hidden = true;
		err.textContent = "";
	}
	setGalleryExportProgress(0, "Preparing download…");
}
function triggerFileDownload(url) {
	var a = document.createElement("a");
	a.href = url;
	a.rel = "noopener";
	document.body.appendChild(a);
	a.click();
	a.remove();
}
function deliverFriendlyExport(downloadUrl) {
	setGalleryExportProgress(100, "Download starting…");
	triggerFileDownload(downloadUrl);
	setTimeout(hideGalleryExportAlert, 1500);
}
function applyGalleryExport(exp) {
	var alertEl;
	var err;
	if (!exp || exp.relative_path !== S.galleryItemPath) {
		return;
	}
	alertEl = document.getElementById("gallery-export-alert");
	err = document.getElementById("gallery-export-error");
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
function startFriendlyExport() {
	var fmt = S.galleryItemKind === "video" ? "h264_aac" : "jpeg";
	var alertEl = document.getElementById("gallery-export-alert");
	hideGalleryExportAlert();
	setGalleryExportProgress(0, "Preparing download…");
	if (alertEl) {
		alertEl.hidden = false;
	}
	R.api("POST", "/api/gallery/export", { relative_path: S.galleryItemPath, format: fmt })
		.then(applyGalleryExport)
		.catch(function (exportErr) {
			applyGalleryExport({
				relative_path: S.galleryItemPath,
				phase: "error",
				percent: 0,
				error: exportErr.message || "Export failed.",
			});
		});
}
function loadGalleryItemDetail(direction) {
	var stage = document.getElementById("gallery-item-stage");
	var title = document.getElementById("gallery-item-title");
	var metaHost = document.getElementById("gallery-item-meta");
	var friendly = document.getElementById("btn-gallery-friendly");
	if (!stage || !S.galleryItemPath) {
		return;
	}
	hideGalleryExportAlert();
	setStageLoading(stage, direction);
	updateGalleryItemNav();
	R.api("GET", "/api/gallery/item?path=" + encodeURIComponent(S.galleryItemPath))
		.then(function (payload) {
			var meta = payload.metadata || {};
			var rows;
			var mp4Ok;
			S.galleryItemKind = payload.kind === "video" ? "video" : "image";
			if (title) {
				title.textContent = meta.filename || payload.relative_path;
			}
			renderGalleryItemStage(stage, payload, meta);
			if (friendly) {
				if (payload.kind === "video") {
					mp4Ok = S.state?.video_friendly_export_available;
					friendly.hidden = !mp4Ok;
					friendly.textContent = "Download as MP4";
				} else {
					friendly.hidden = false;
					friendly.textContent = "Download as JPEG";
				}
			}
			if (metaHost) {
				rows = [
					["On disk", payload.absolute_path || "—"],
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
				if (payload.kind === "video") {
					rows.push(["Duration", formatDuration(meta.duration_seconds)]);
				}
				if (meta.gps) {
					rows.push(["Location", meta.gps]);
				}
				metaHost.innerHTML = "";
				rows.forEach(function (row) {
					var dt = document.createElement("dt");
					var dd = document.createElement("dd");
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
		.catch(function () {
			setStageMessage(stage, "Could not load this item.");
			updateGalleryItemNav();
		});
}
R.pathLooksLikeVideo = pathLooksLikeVideo;
R.prefetchGalleryMedia = prefetchGalleryMedia;
R.setStageLoading = setStageLoading;
R.setStageMessage = setStageMessage;
R.revealGalleryFull = revealGalleryFull;
R.renderGalleryItemStage = renderGalleryItemStage;
R.galleryItemPathFromLocation = galleryItemPathFromLocation;
R.closeGalleryPhonePopup = closeGalleryPhonePopup;
R.toggleGalleryPhonePopup = toggleGalleryPhonePopup;
R.syncGalleryPhoneHelpVisibility = syncGalleryPhoneHelpVisibility;
R.fetchGalleryNeighbor = fetchGalleryNeighbor;
R.refreshGalleryItemNeighbors = refreshGalleryItemNeighbors;
R.updateGalleryItemNav = updateGalleryItemNav;
R.shiftGalleryItem = shiftGalleryItem;
R.showGalleryItem = showGalleryItem;
R.appendThumbCell = appendThumbCell;
R.formatFileSize = formatFileSize;
R.formatDuration = formatDuration;
R.formatCaptured = formatCaptured;
R.setGalleryExportProgress = setGalleryExportProgress;
R.hideGalleryExportAlert = hideGalleryExportAlert;
R.triggerFileDownload = triggerFileDownload;
R.deliverFriendlyExport = deliverFriendlyExport;
R.applyGalleryExport = applyGalleryExport;
R.startFriendlyExport = startFriendlyExport;
R.loadGalleryItemDetail = loadGalleryItemDetail;

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
