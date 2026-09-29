import { apiSend } from "./api.ts";
import { appendThumbCell } from "./gallery-item.ts";
import { monthName } from "./home.ts";
import { S } from "./state.ts";
import type {
	GalleryCalendarResponse,
	GalleryDayResponse,
	GalleryItem,
	GalleryMonthBlock,
	GalleryTimelinePage,
	ServerInfo,
} from "./types.ts";

interface GalleryDateParts {
	year: number;
	month: number;
}

function galleryDateParts(iso: string): GalleryDateParts {
	const d = new Date(iso);
	return { year: d.getFullYear(), month: d.getMonth() + 1 };
}
function buildGalleryMonthBlockElement(block: GalleryMonthBlock): HTMLElement {
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
function appendGalleryTimelineItems(items: GalleryItem[]): void {
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
function unmountGalleryMonthBlock(block: GalleryMonthBlock): void {
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
function remountGalleryMonthBlock(block: GalleryMonthBlock): void {
	const built = buildGalleryMonthBlockElement(block);
	block.placeholderEl?.replaceWith(built);
	block.el = built;
	block.placeholderEl = null;
	block.mounted = true;
	S.galleryMountedTileCount += block.items.length;
}
function enforceGalleryWindow(): void {
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
function scheduleGalleryWindowCheck(): void {
	if (S.galleryWindowCheckScheduled) {
		return;
	}
	S.galleryWindowCheckScheduled = true;
	window.requestAnimationFrame(() => {
		S.galleryWindowCheckScheduled = false;
		enforceGalleryWindow();
	});
}
function ensureGalleryWindowListeners(): void {
	if (S.galleryWindowListenersBound) {
		return;
	}
	S.galleryWindowListenersBound = true;
	window.addEventListener("scroll", scheduleGalleryWindowCheck, { passive: true });
	window.addEventListener("resize", scheduleGalleryWindowCheck);
}
function setGalleryLoadingMoreVisible(visible: boolean): void {
	const el = document.getElementById("gallery-loading-more");
	if (el) {
		el.hidden = !visible;
	}
}
function hideGallerySentinel(): void {
	const el = document.getElementById("gallery-scroll-sentinel");
	if (el) {
		el.hidden = true;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
	}
}
function ensureGallerySentinel(): void {
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
function setupGalleryIntersectionObserver(): void {
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
function showGalleryTimelineMessage(message: string): void {
	const host = document.getElementById("timeline-view");
	if (host) {
		host.innerHTML = '<p class="status-line">' + message + "</p>";
	}
}
function fetchGalleryTimelinePage(): void {
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
	function failLoad(): void {
		S.galleryLoadingMore = false;
		setGalleryLoadingMoreVisible(false);
		S.galleryHasMore = false;
		hideGallerySentinel();
		if (isFirstPage) {
			showGalleryTimelineMessage("Could not load gallery.");
		}
	}
	apiSend<GalleryTimelinePage>("GET", url)
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
function cssTimeToMs(value: string): number {
	const token = value.trim();
	const n = Number.parseFloat(token);
	if (Number.isNaN(n)) {
		return 0;
	}
	return token.endsWith("ms") ? n : n * 1000;
}
/** Drop a deleted item from the in-memory timeline (and its now-empty month block, if any). */
function forgetGalleryItem(relativePath: string): void {
	const blockIndex = S.galleryMonthBlocks.findIndex((b) => b.items.some((i) => i.relative_path === relativePath));
	const block = S.galleryMonthBlocks[blockIndex];
	if (!block) {
		return;
	}
	block.items = block.items.filter((i) => i.relative_path !== relativePath);
	if (block.mounted) {
		S.galleryMountedTileCount -= 1;
	}
	if (block.items.length > 0) {
		return;
	}
	block.el?.remove();
	block.placeholderEl?.remove();
	S.galleryMonthBlocks.splice(blockIndex, 1);
	const next = S.galleryMonthBlocks[blockIndex];
	if (block.showYear && next && next.year === block.year && !next.showYear) {
		// The year heading lived on the removed block; hand it to the next month of that year.
		next.showYear = true;
		if (next.mounted && next.el) {
			const rebuilt = buildGalleryMonthBlockElement(next);
			next.el.replaceWith(rebuilt);
			next.el = rebuilt;
		}
	}
	if (S.galleryMonthBlocks.length === 0 && !S.galleryHasMore) {
		showGalleryTimelineMessage("No saved media yet");
	}
}
/**
 * Remove a just-deleted item from the timeline *in place* — no reload, so there is no blank
 * flash and the scroll position is untouched. A still-mounted tile fades/shrinks out first
 * (after the screen's own fade-in, `--dur-base`, or the two fades overlap and the removal goes
 * unseen); an unmounted one is simply forgotten. Removal never depends on `transitionend`: a
 * timeout slightly past the fade's `--dur-base` guarantees it (also covers reduced motion,
 * where `--dur-base` is ~0).
 */
function removeGalleryItem(relativePath: string): void {
	const tile = Array.from(document.querySelectorAll<HTMLElement>("#timeline-view .thumb-link")).find(
		(el) => el.querySelector("img")?.alt === relativePath,
	);
	if (!tile) {
		forgetGalleryItem(relativePath);
		return;
	}
	let finished = false;
	const finish = (): void => {
		if (finished) {
			return;
		}
		finished = true;
		tile.remove();
		forgetGalleryItem(relativePath);
	};
	const base = cssTimeToMs(getComputedStyle(document.documentElement).getPropertyValue("--dur-base"));
	window.setTimeout(() => {
		tile.classList.add("thumb-removing");
		tile.addEventListener("transitionend", finish, { once: true });
		window.setTimeout(finish, base + 100);
	}, base);
}
function loadGallery(): void {
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
function daysInMonth(year: number, month: number): number {
	return new Date(year, month, 0).getDate();
}
function shiftCalendarMonth(delta: number): void {
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
function renderCalendarGrid(daysWithMedia: number[]): void {
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
	const mediaSet: Record<number, boolean> = {};
	daysWithMedia.forEach((d) => {
		mediaSet[d] = true;
	});
	for (let day = 1; day <= total; day += 1) {
		let cell: HTMLElement;
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
function selectCalendarDay(day: number): void {
	S.calendarSelectedDay = day;
	loadCalendarMonth();
	apiSend<GalleryDayResponse>(
		"GET",
		"/api/gallery/day?year=" + S.calendarYear + "&month=" + S.calendarMonth + "&day=" + day,
	)
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
function loadCalendarMonth(): void {
	apiSend<GalleryCalendarResponse>("GET", "/api/gallery/calendar?year=" + S.calendarYear + "&month=" + S.calendarMonth)
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
function setGalleryQrPlaceholder(placeholderEl: HTMLElement | null, qrUrl: string | undefined): void {
	if (!placeholderEl) {
		return;
	}
	placeholderEl.innerHTML = "";
	const img = document.createElement("img");
	img.src = qrUrl || "/api/gallery/qr.svg";
	img.alt = "QR code for gallery URL";
	placeholderEl.appendChild(img);
}
function applyGalleryFirewallHints(info: ServerInfo, hintEl: HTMLElement | null, fwWarnEl: HTMLElement | null): void {
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
function loadServerInfo(): void {
	apiSend<ServerInfo>("GET", "/api/server-info").then((info) => {
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
	removeGalleryItem,
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
