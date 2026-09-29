import { apiSend } from "./api.js";
import { appendThumbCell } from "./gallery-item.js";
import { monthName } from "./home.js";
import { S } from "./state.js";

function galleryDateParts(iso) {
	const d = new Date(iso);
	return { year: d.getFullYear(), month: d.getMonth() + 1 };
}
function buildGalleryMonthBlockElement(block) {
	const wrap = document.createElement("div");
	wrap.className = "month-block";
	if (block.showYear) {
		const yTitle = document.createElement("h3");
		yTitle.className = "year-title";
		yTitle.textContent = String(block.year);
		wrap.appendChild(yTitle);
	}
	const mLabel = document.createElement("p");
	mLabel.className = "month-label";
	mLabel.textContent = monthName(block.month);
	wrap.appendChild(mLabel);
	const grid = document.createElement("div");
	grid.className = "thumb-grid";
	block.items.forEach((item) => {
		appendThumbCell(grid, item);
	});
	wrap.appendChild(grid);
	return wrap;
}
function appendGalleryTimelineItems(items) {
	const host = document.getElementById("timeline-view");
	const sentinel = document.getElementById("gallery-scroll-sentinel");
	if (!host) {
		return;
	}
	items.forEach((item) => {
		const parts = galleryDateParts(item.captured_at);
		let lastBlock = S.galleryMonthBlocks[S.galleryMonthBlocks.length - 1];
		if (!lastBlock || lastBlock.year !== parts.year || lastBlock.month !== parts.month) {
			lastBlock = {
				year: parts.year,
				month: parts.month,
				showYear: !lastBlock || lastBlock.year !== parts.year,
				items: [],
				el: null,
				placeholderEl: null,
				mounted: true,
			};
			S.galleryMonthBlocks.push(lastBlock);
			lastBlock.el = buildGalleryMonthBlockElement(lastBlock);
			host.insertBefore(lastBlock.el, sentinel);
		}
		lastBlock.items.push(item);
		if (lastBlock.mounted) {
			const grid = lastBlock.el?.querySelector(".thumb-grid");
			if (grid) {
				appendThumbCell(grid, item);
			}
			S.galleryMountedTileCount += 1;
		}
	});
}
function unmountGalleryMonthBlock(block) {
	if (!block.el) {
		return;
	}
	const height = block.el.getBoundingClientRect().height;
	const placeholder = document.createElement("div");
	placeholder.className = "month-placeholder";
	placeholder.style.height = height + "px";
	block.el.replaceWith(placeholder);
	block.placeholderEl = placeholder;
	block.el = null;
	block.mounted = false;
	S.galleryMountedTileCount -= block.items.length;
}
function remountGalleryMonthBlock(block) {
	const built = buildGalleryMonthBlockElement(block);
	block.placeholderEl?.replaceWith(built);
	block.el = built;
	block.placeholderEl = null;
	block.mounted = true;
	S.galleryMountedTileCount += block.items.length;
}
function enforceGalleryWindow() {
	if (!S.galleryMonthBlocks.length || !window.innerHeight) {
		return;
	}
	const buffer = window.innerHeight * S.GALLERY_VIEWPORT_BUFFER_MULTIPLIER;
	for (let i = 0; i < S.galleryMonthBlocks.length && S.galleryMountedTileCount > S.GALLERY_TILE_BUDGET; i += 1) {
		const block = S.galleryMonthBlocks[i];
		if (!block?.mounted || !block.el) {
			continue;
		}
		const rect = block.el.getBoundingClientRect();
		if (rect.bottom < -buffer) {
			unmountGalleryMonthBlock(block);
		} else {
			break;
		}
	}
	for (let i = 0; i < S.galleryMonthBlocks.length; i += 1) {
		const block = S.galleryMonthBlocks[i];
		if (!block || block.mounted || !block.placeholderEl) {
			continue;
		}
		const rect = block.placeholderEl.getBoundingClientRect();
		if (rect.bottom >= -buffer && rect.top <= window.innerHeight + buffer) {
			remountGalleryMonthBlock(block);
		}
	}
}
function scheduleGalleryWindowCheck() {
	if (S.galleryWindowCheckScheduled) {
		return;
	}
	S.galleryWindowCheckScheduled = true;
	window.requestAnimationFrame(() => {
		S.galleryWindowCheckScheduled = false;
		enforceGalleryWindow();
	});
}
function ensureGalleryWindowListeners() {
	if (S.galleryWindowListenersBound) {
		return;
	}
	S.galleryWindowListenersBound = true;
	window.addEventListener("scroll", scheduleGalleryWindowCheck, { passive: true });
	window.addEventListener("resize", scheduleGalleryWindowCheck);
}
function setGalleryLoadingMoreVisible(visible) {
	const el = document.getElementById("gallery-loading-more");
	if (el) {
		el.hidden = !visible;
	}
}
function hideGallerySentinel() {
	const el = document.getElementById("gallery-scroll-sentinel");
	if (el) {
		el.hidden = true;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
	}
}
function ensureGallerySentinel() {
	const host = document.getElementById("timeline-view");
	if (!host) {
		return;
	}
	const loading = document.createElement("p");
	loading.className = "status-line gallery-loading-more";
	loading.id = "gallery-loading-more";
	loading.hidden = true;
	loading.innerHTML = '<span class="gallery-loading-spinner" aria-hidden="true"></span> Loading more…';
	const sentinel = document.createElement("div");
	sentinel.id = "gallery-scroll-sentinel";
	host.appendChild(loading);
	host.appendChild(sentinel);
}
function setupGalleryIntersectionObserver() {
	const sentinel = document.getElementById("gallery-scroll-sentinel");
	if (!sentinel || typeof IntersectionObserver === "undefined") {
		return;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
	}
	S.galleryIntersectionObserver = new IntersectionObserver(
		(entries) => {
			entries.forEach((entry) => {
				if (entry.isIntersecting && S.galleryHasMore && !S.galleryLoadingMore) {
					fetchGalleryTimelinePage();
				}
			});
		},
		{ rootMargin: "600px 0px" },
	);
	S.galleryIntersectionObserver.observe(sentinel);
}
function showGalleryTimelineMessage(message) {
	const host = document.getElementById("timeline-view");
	if (host) {
		host.innerHTML = '<p class="status-line">' + message + "</p>";
	}
}
function fetchGalleryTimelinePage() {
	const isFirstPage = S.galleryMonthBlocks.length === 0;
	let url = "/api/gallery/timeline?limit=" + S.GALLERY_PAGE_LIMIT;
	if (S.galleryLoadingMore) {
		return;
	}
	if (S.galleryNextCursor) {
		url += "&cursor=" + encodeURIComponent(S.galleryNextCursor);
	}
	S.galleryLoadingMore = true;
	setGalleryLoadingMoreVisible(true);
	function failLoad() {
		S.galleryLoadingMore = false;
		setGalleryLoadingMoreVisible(false);
		S.galleryHasMore = false;
		hideGallerySentinel();
		if (isFirstPage) {
			showGalleryTimelineMessage("Could not load gallery.");
		}
	}
	apiSend("GET", url)
		.then((payload) => {
			const items = payload.items || [];
			S.galleryLoadingMore = false;
			setGalleryLoadingMoreVisible(false);
			S.galleryNextCursor = payload.next_cursor || null;
			S.galleryHasMore = Boolean(S.galleryNextCursor);
			if (isFirstPage && !items.length) {
				showGalleryTimelineMessage("No saved media yet");
				S.galleryHasMore = false;
				return;
			}
			appendGalleryTimelineItems(items);
			if (!S.galleryHasMore) {
				hideGallerySentinel();
			}
			scheduleGalleryWindowCheck();
		})
		.catch(failLoad);
}
/** Duration of a CSS time token such as `200ms` / `0.2s` / `0.001ms`, in ms (0 if unparseable). */
function cssTimeToMs(value) {
	const token = value.trim();
	const n = Number.parseFloat(token);
	if (Number.isNaN(n)) {
		return 0;
	}
	return token.endsWith("ms") ? n : n * 1000;
}
/**
 * Fade/shrink out the still-mounted thumbnail of a just-deleted item, remove it, then call
 * `onDone` exactly once. Returns false (nothing scheduled, `onDone` not called) when the tile
 * is not mounted, so the caller can fall back to a plain reload. Removal does not depend on
 * `transitionend`: a timeout slightly past `--dur-base` guarantees it (also covers reduced
 * motion, where `--dur-base` is ~0).
 */
function removeGalleryThumb(relativePath, onDone) {
	const tile = Array.from(document.querySelectorAll("#timeline-view .thumb-link")).find(
		(el) => el.querySelector("img")?.alt === relativePath,
	);
	if (!tile) {
		return false;
	}
	let finished = false;
	const finish = () => {
		if (finished) {
			return;
		}
		finished = true;
		tile.remove();
		onDone();
	};
	const base = cssTimeToMs(getComputedStyle(document.documentElement).getPropertyValue("--dur-base"));
	// Next frame so the tile has painted its start state and the transition actually runs.
	requestAnimationFrame(() => {
		tile.classList.add("thumb-removing");
		tile.addEventListener("transitionend", finish, { once: true });
		window.setTimeout(finish, base + 100);
	});
	return true;
}
function loadGallery() {
	const host = document.getElementById("timeline-view");
	if (!host) {
		return;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
		S.galleryIntersectionObserver = null;
	}
	S.galleryMonthBlocks = [];
	S.galleryNextCursor = null;
	S.galleryHasMore = true;
	S.galleryLoadingMore = false;
	S.galleryMountedTileCount = 0;
	host.innerHTML = "";
	ensureGallerySentinel();
	ensureGalleryWindowListeners();
	setupGalleryIntersectionObserver();
	fetchGalleryTimelinePage();
}
function daysInMonth(year, month) {
	return new Date(year, month, 0).getDate();
}
function shiftCalendarMonth(delta) {
	S.calendarMonth += delta;
	if (S.calendarMonth > 12) {
		S.calendarMonth = 1;
		S.calendarYear += 1;
	} else if (S.calendarMonth < 1) {
		S.calendarMonth = 12;
		S.calendarYear -= 1;
	}
	S.calendarSelectedDay = null;
	loadCalendarMonth();
}
function renderCalendarGrid(daysWithMedia) {
	const grid = document.getElementById("calendar-grid");
	const title = document.getElementById("calendar-title");
	if (!grid || !title) {
		return;
	}
	title.textContent = monthName(S.calendarMonth) + " " + S.calendarYear;
	grid.innerHTML = "";
	["M", "T", "W", "T", "F", "S", "S"].forEach((label) => {
		const wd = document.createElement("span");
		wd.className = "cal-cell weekday";
		wd.textContent = label;
		grid.appendChild(wd);
	});
	const firstDow = new Date(S.calendarYear, S.calendarMonth - 1, 1).getDay();
	const lead = (firstDow + 6) % 7;
	for (let i = 0; i < lead; i += 1) {
		const blank = document.createElement("span");
		blank.className = "cal-cell";
		grid.appendChild(blank);
	}
	const total = daysInMonth(S.calendarYear, S.calendarMonth);
	const mediaSet = {};
	daysWithMedia.forEach((d) => {
		mediaSet[d] = true;
	});
	for (let day = 1; day <= total; day += 1) {
		let cell;
		if (mediaSet[day]) {
			const btn = document.createElement("button");
			btn.type = "button";
			btn.className = "cal-cell has-media";
			if (S.calendarSelectedDay === day) {
				btn.classList.add("selected");
			}
			btn.textContent = String(day);
			btn.addEventListener("click", () => {
				selectCalendarDay(day);
			});
			cell = btn;
		} else {
			const span = document.createElement("span");
			span.className = "cal-cell";
			span.textContent = String(day);
			cell = span;
		}
		grid.appendChild(cell);
	}
}
function selectCalendarDay(day) {
	S.calendarSelectedDay = day;
	loadCalendarMonth();
	apiSend("GET", "/api/gallery/day?year=" + S.calendarYear + "&month=" + S.calendarMonth + "&day=" + day)
		.then((payload) => {
			const label = document.getElementById("calendar-day-label");
			const thumbs = document.getElementById("calendar-day-thumbs");
			if (!label || !thumbs) {
				return;
			}
			label.hidden = false;
			label.textContent = monthName(S.calendarMonth) + " " + day + ", " + S.calendarYear;
			thumbs.innerHTML = "";
			if (!payload.items?.length) {
				thumbs.innerHTML = '<p class="status-line">No items for this day.</p>';
				return;
			}
			payload.items.forEach((item) => {
				appendThumbCell(thumbs, item);
			});
		})
		.catch(() => {
			const thumbs = document.getElementById("calendar-day-thumbs");
			if (thumbs) {
				thumbs.innerHTML = '<p class="status-line">Could not load day.</p>';
			}
		});
}
function loadCalendarMonth() {
	apiSend("GET", "/api/gallery/calendar?year=" + S.calendarYear + "&month=" + S.calendarMonth)
		.then((payload) => {
			renderCalendarGrid(payload.days_with_media || []);
			if (S.calendarSelectedDay === null) {
				const label = document.getElementById("calendar-day-label");
				const thumbs = document.getElementById("calendar-day-thumbs");
				if (label) {
					label.hidden = true;
				}
				if (thumbs) {
					thumbs.innerHTML = "";
				}
			}
		})
		.catch(() => {
			const grid = document.getElementById("calendar-grid");
			if (grid) {
				grid.innerHTML = '<p class="status-line">Could not load calendar.</p>';
			}
		});
}
function setGalleryQrPlaceholder(placeholderEl, qrUrl) {
	if (!placeholderEl) {
		return;
	}
	placeholderEl.innerHTML = "";
	const img = document.createElement("img");
	img.src = qrUrl || "/api/gallery/qr.svg";
	img.alt = "QR code for gallery URL";
	placeholderEl.appendChild(img);
}
function applyGalleryFirewallHints(info, hintEl, fwWarnEl) {
	if (hintEl) {
		const showHint = info.lan_reachable === false;
		hintEl.hidden = !showHint;
	}
	const fw = info.firewall;
	if (fwWarnEl) {
		if (fw.port_open === false && fw.message) {
			fwWarnEl.textContent = fw.message;
			fwWarnEl.hidden = false;
		} else if (fw.port_open === null && fw.message && info.lan_reachable) {
			fwWarnEl.textContent = fw.message;
			fwWarnEl.hidden = false;
		} else {
			fwWarnEl.hidden = true;
			fwWarnEl.textContent = "";
		}
	}
}
function loadServerInfo() {
	apiSend("GET", "/api/server-info").then((info) => {
		const qr = document.getElementById("qr-placeholder");
		const urlField = document.getElementById("gallery-url");
		const popupUrl = document.getElementById("gallery-popup-url");
		const portLabel = document.getElementById("gallery-lan-port");
		const galleryUrl = info.gallery_url || "";
		setGalleryQrPlaceholder(qr, info.qr_url);
		setGalleryQrPlaceholder(document.getElementById("gallery-popup-qr"), info.qr_url);
		if (urlField) {
			urlField.textContent = galleryUrl;
		}
		if (popupUrl) {
			popupUrl.textContent = galleryUrl;
		}
		const portText = info.port ? String(info.port) : "8765";
		if (portLabel) {
			portLabel.textContent = portText;
		}
		document.querySelectorAll(".lan-firewall-port").forEach((el) => {
			el.textContent = portText;
		});
		applyGalleryFirewallHints(
			info,
			document.getElementById("gallery-lan-hint"),
			document.getElementById("gallery-firewall-warn"),
		);
		applyGalleryFirewallHints(
			info,
			document.getElementById("gallery-popup-lan-hint"),
			document.getElementById("gallery-popup-firewall-warn"),
		);
	});
}

export {
	appendGalleryTimelineItems,
	applyGalleryFirewallHints,
	buildGalleryMonthBlockElement,
	daysInMonth,
	enforceGalleryWindow,
	ensureGallerySentinel,
	ensureGalleryWindowListeners,
	fetchGalleryTimelinePage,
	galleryDateParts,
	hideGallerySentinel,
	loadCalendarMonth,
	loadGallery,
	loadServerInfo,
	remountGalleryMonthBlock,
	removeGalleryThumb,
	renderCalendarGrid,
	scheduleGalleryWindowCheck,
	selectCalendarDay,
	setGalleryLoadingMoreVisible,
	setGalleryQrPlaceholder,
	setupGalleryIntersectionObserver,
	shiftCalendarMonth,
	showGalleryTimelineMessage,
	unmountGalleryMonthBlock,
};
