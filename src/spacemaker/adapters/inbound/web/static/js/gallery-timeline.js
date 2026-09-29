// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function galleryDateParts(iso) {
	var d = new Date(iso);
	return { year: d.getFullYear(), month: d.getMonth() + 1 };
}
function buildGalleryMonthBlockElement(block) {
	var wrap = document.createElement("div");
	var yTitle;
	var mLabel;
	var grid;
	wrap.className = "month-block";
	if (block.showYear) {
		yTitle = document.createElement("h3");
		yTitle.className = "year-title";
		yTitle.textContent = String(block.year);
		wrap.appendChild(yTitle);
	}
	mLabel = document.createElement("p");
	mLabel.className = "month-label";
	mLabel.textContent = R.monthName(block.month);
	wrap.appendChild(mLabel);
	grid = document.createElement("div");
	grid.className = "thumb-grid";
	block.items.forEach(function (item) {
		R.appendThumbCell(grid, item);
	});
	wrap.appendChild(grid);
	return wrap;
}
function appendGalleryTimelineItems(items) {
	var host = document.getElementById("timeline-view");
	var sentinel = document.getElementById("gallery-scroll-sentinel");
	if (!host) {
		return;
	}
	items.forEach(function (item) {
		var parts = galleryDateParts(item.captured_at);
		var lastBlock = S.galleryMonthBlocks[S.galleryMonthBlocks.length - 1];
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
			R.appendThumbCell(lastBlock.el.querySelector(".thumb-grid"), item);
			S.galleryMountedTileCount += 1;
		}
	});
}
function unmountGalleryMonthBlock(block) {
	var height = block.el.getBoundingClientRect().height;
	var placeholder = document.createElement("div");
	placeholder.className = "month-placeholder";
	placeholder.style.height = height + "px";
	block.el.replaceWith(placeholder);
	block.placeholderEl = placeholder;
	block.el = null;
	block.mounted = false;
	S.galleryMountedTileCount -= block.items.length;
}
function remountGalleryMonthBlock(block) {
	var built = buildGalleryMonthBlockElement(block);
	block.placeholderEl.replaceWith(built);
	block.el = built;
	block.placeholderEl = null;
	block.mounted = true;
	S.galleryMountedTileCount += block.items.length;
}
function enforceGalleryWindow() {
	if (!S.galleryMonthBlocks.length || !window.innerHeight) {
		return;
	}
	var buffer = window.innerHeight * S.GALLERY_VIEWPORT_BUFFER_MULTIPLIER;
	var i;
	var block;
	var rect;
	for (i = 0; i < S.galleryMonthBlocks.length && S.galleryMountedTileCount > S.GALLERY_TILE_BUDGET; i += 1) {
		block = S.galleryMonthBlocks[i];
		if (!block.mounted) {
			continue;
		}
		rect = block.el.getBoundingClientRect();
		if (rect.bottom < -buffer) {
			unmountGalleryMonthBlock(block);
		} else {
			break;
		}
	}
	for (i = 0; i < S.galleryMonthBlocks.length; i += 1) {
		block = S.galleryMonthBlocks[i];
		if (block.mounted) {
			continue;
		}
		rect = block.placeholderEl.getBoundingClientRect();
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
	window.requestAnimationFrame(function () {
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
	var el = document.getElementById("gallery-loading-more");
	if (el) {
		el.hidden = !visible;
	}
}
function hideGallerySentinel() {
	var el = document.getElementById("gallery-scroll-sentinel");
	if (el) {
		el.hidden = true;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
	}
}
function ensureGallerySentinel() {
	var host = document.getElementById("timeline-view");
	var loading;
	var sentinel;
	if (!host) {
		return;
	}
	loading = document.createElement("p");
	loading.className = "status-line gallery-loading-more";
	loading.id = "gallery-loading-more";
	loading.hidden = true;
	loading.innerHTML = '<span class="gallery-loading-spinner" aria-hidden="true"></span> Loading more…';
	sentinel = document.createElement("div");
	sentinel.id = "gallery-scroll-sentinel";
	host.appendChild(loading);
	host.appendChild(sentinel);
}
function setupGalleryIntersectionObserver() {
	var sentinel = document.getElementById("gallery-scroll-sentinel");
	if (!sentinel || typeof IntersectionObserver === "undefined") {
		return;
	}
	if (S.galleryIntersectionObserver) {
		S.galleryIntersectionObserver.disconnect();
	}
	S.galleryIntersectionObserver = new IntersectionObserver(
		function (entries) {
			entries.forEach(function (entry) {
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
	var host = document.getElementById("timeline-view");
	if (host) {
		host.innerHTML = '<p class="status-line">' + message + "</p>";
	}
}
function fetchGalleryTimelinePage() {
	var isFirstPage = S.galleryMonthBlocks.length === 0;
	var url = "/api/gallery/timeline?limit=" + S.GALLERY_PAGE_LIMIT;
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
	if (typeof R.api !== "function") {
		failLoad();
		return;
	}
	try {
		R.api("GET", url)
			.then(function (payload) {
				var items = payload.items || [];
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
	} catch (_err) {
		failLoad();
	}
}
function loadGallery() {
	var host = document.getElementById("timeline-view");
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
	var grid = document.getElementById("calendar-grid");
	var title = document.getElementById("calendar-title");
	var firstDow;
	var lead;
	var i;
	var blank;
	var total;
	var mediaSet = {};
	var day;
	var cell;
	if (!grid || !title) {
		return;
	}
	title.textContent = R.monthName(S.calendarMonth) + " " + S.calendarYear;
	grid.innerHTML = "";
	["M", "T", "W", "T", "F", "S", "S"].forEach(function (label) {
		var wd = document.createElement("span");
		wd.className = "cal-cell weekday";
		wd.textContent = label;
		grid.appendChild(wd);
	});
	firstDow = new Date(S.calendarYear, S.calendarMonth - 1, 1).getDay();
	lead = (firstDow + 6) % 7;
	for (i = 0; i < lead; i += 1) {
		blank = document.createElement("span");
		blank.className = "cal-cell";
		grid.appendChild(blank);
	}
	total = daysInMonth(S.calendarYear, S.calendarMonth);
	daysWithMedia.forEach(function (d) {
		mediaSet[d] = true;
	});
	for (day = 1; day <= total; day += 1) {
		if (mediaSet[day]) {
			cell = document.createElement("button");
			cell.type = "button";
			cell.className = "cal-cell has-media";
			if (S.calendarSelectedDay === day) {
				cell.classList.add("selected");
			}
			cell.textContent = String(day);
			cell.addEventListener(
				"click",
				(function (d) {
					return function () {
						selectCalendarDay(d);
					};
				})(day),
			);
		} else {
			cell = document.createElement("span");
			cell.className = "cal-cell";
			cell.textContent = String(day);
		}
		grid.appendChild(cell);
	}
}
function selectCalendarDay(day) {
	S.calendarSelectedDay = day;
	loadCalendarMonth();
	R.api("GET", "/api/gallery/day?year=" + S.calendarYear + "&month=" + S.calendarMonth + "&day=" + day)
		.then(function (payload) {
			var label = document.getElementById("calendar-day-label");
			var thumbs = document.getElementById("calendar-day-thumbs");
			if (!label || !thumbs) {
				return;
			}
			label.hidden = false;
			label.textContent = R.monthName(S.calendarMonth) + " " + day + ", " + S.calendarYear;
			thumbs.innerHTML = "";
			if (!payload.items?.length) {
				thumbs.innerHTML = '<p class="status-line">No items for this day.</p>';
				return;
			}
			payload.items.forEach(function (item) {
				R.appendThumbCell(thumbs, item);
			});
		})
		.catch(function () {
			var thumbs = document.getElementById("calendar-day-thumbs");
			if (thumbs) {
				thumbs.innerHTML = '<p class="status-line">Could not load day.</p>';
			}
		});
}
function loadCalendarMonth() {
	R.api("GET", "/api/gallery/calendar?year=" + S.calendarYear + "&month=" + S.calendarMonth)
		.then(function (payload) {
			var label;
			var thumbs;
			renderCalendarGrid(payload.days_with_media || []);
			if (S.calendarSelectedDay === null) {
				label = document.getElementById("calendar-day-label");
				thumbs = document.getElementById("calendar-day-thumbs");
				if (label) {
					label.hidden = true;
				}
				if (thumbs) {
					thumbs.innerHTML = "";
				}
			}
		})
		.catch(function () {
			var grid = document.getElementById("calendar-grid");
			if (grid) {
				grid.innerHTML = '<p class="status-line">Could not load calendar.</p>';
			}
		});
}
function setGalleryQrPlaceholder(placeholderEl, qrUrl) {
	var img;
	if (!placeholderEl) {
		return;
	}
	placeholderEl.innerHTML = "";
	img = document.createElement("img");
	img.src = qrUrl || "/api/gallery/qr.svg";
	img.alt = "QR code for gallery URL";
	placeholderEl.appendChild(img);
}
function applyGalleryFirewallHints(info, hintEl, fwWarnEl) {
	var showHint;
	var fw;
	if (hintEl) {
		showHint = info.lan_reachable === false;
		hintEl.hidden = !showHint;
	}
	fw = info.firewall || {};
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
	R.api("GET", "/api/server-info").then(function (info) {
		var qr = document.getElementById("qr-placeholder");
		var urlField = document.getElementById("gallery-url");
		var popupUrl = document.getElementById("gallery-popup-url");
		var portLabel = document.getElementById("gallery-lan-port");
		var portText;
		var galleryUrl = info.gallery_url || "";
		setGalleryQrPlaceholder(qr, info.qr_url);
		setGalleryQrPlaceholder(document.getElementById("gallery-popup-qr"), info.qr_url);
		if (urlField) {
			urlField.textContent = galleryUrl;
		}
		if (popupUrl) {
			popupUrl.textContent = galleryUrl;
		}
		portText = info.port ? String(info.port) : "8765";
		if (portLabel) {
			portLabel.textContent = portText;
		}
		document.querySelectorAll(".lan-firewall-port").forEach(function (el) {
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
R.galleryDateParts = galleryDateParts;
R.buildGalleryMonthBlockElement = buildGalleryMonthBlockElement;
R.appendGalleryTimelineItems = appendGalleryTimelineItems;
R.unmountGalleryMonthBlock = unmountGalleryMonthBlock;
R.remountGalleryMonthBlock = remountGalleryMonthBlock;
R.enforceGalleryWindow = enforceGalleryWindow;
R.scheduleGalleryWindowCheck = scheduleGalleryWindowCheck;
R.ensureGalleryWindowListeners = ensureGalleryWindowListeners;
R.setGalleryLoadingMoreVisible = setGalleryLoadingMoreVisible;
R.hideGallerySentinel = hideGallerySentinel;
R.ensureGallerySentinel = ensureGallerySentinel;
R.setupGalleryIntersectionObserver = setupGalleryIntersectionObserver;
R.showGalleryTimelineMessage = showGalleryTimelineMessage;
R.fetchGalleryTimelinePage = fetchGalleryTimelinePage;
R.loadGallery = loadGallery;
R.daysInMonth = daysInMonth;
R.shiftCalendarMonth = shiftCalendarMonth;
R.renderCalendarGrid = renderCalendarGrid;
R.selectCalendarDay = selectCalendarDay;
R.loadCalendarMonth = loadCalendarMonth;
R.setGalleryQrPlaceholder = setGalleryQrPlaceholder;
R.applyGalleryFirewallHints = applyGalleryFirewallHints;
R.loadServerInfo = loadServerInfo;

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
