import { ApiError, apiSend } from "./api.js";
import { bindLightbox, closeLightbox, openLightbox, syncLightboxSelection } from "./device-lightbox.js";
import {
	createThumbLoader,
	formatMediaDuration,
	isImageName,
	isPreviewableVideo,
	isVideoName,
} from "./device-preview.js";
import { onClick } from "./dom.js";
import { showView } from "./shell.js";

const MEDIA_EXTENSIONS = new Set([
	"arw",
	"avif",
	"cr2",
	"cr3",
	"dng",
	"heic",
	"heif",
	"jpeg",
	"jpg",
	"jxl",
	"nef",
	"nrw",
	"orf",
	"pef",
	"png",
	"raf",
	"rw2",
	"sr2",
	"srf",
	"srw",
	"tiff",
	"webp",
	"avi",
	"m2ts",
	"m4v",
	"mkv",
	"mov",
	"mp4",
	"mts",
	"webm",
]);
const PAGE_SIZE = 100;
const FILTER_DEBOUNCE_MS = 200;
const SORT_NATURAL_ORDER = { name: "asc", mtime: "desc", size: "desc" };
const COLUMN_LABEL = { name: "Name", mtime: "Modified", size: "Size" };
const SORT_LABEL = {
	"name:asc": "Name, A → Z",
	"name:desc": "Name, Z → A",
	"mtime:desc": "Newest first",
	"mtime:asc": "Oldest first",
	"size:desc": "Largest first",
	"size:asc": "Smallest first",
};
let session = null;
function el(id) {
	return document.getElementById(id);
}
function rootName(method) {
	return method === "afc" ? "iPhone" : "Phone storage";
}
function joinPath(dir, name) {
	return dir ? dir + "/" + name : name;
}
function formatSize(bytes) {
	const kb = 1024;
	const mb = kb * kb;
	if (bytes >= mb) {
		return (bytes / mb).toFixed(1) + " MB";
	}
	if (bytes >= kb) {
		return Math.round(bytes / kb) + " KB";
	}
	return bytes + " B";
}
function formatDate(epochSeconds) {
	if (!epochSeconds) {
		return "—";
	}
	const d = new Date(epochSeconds * 1000);
	const mm = String(d.getMonth() + 1).padStart(2, "0");
	const dd = String(d.getDate()).padStart(2, "0");
	return d.getFullYear() + "-" + mm + "-" + dd;
}
function isMediaName(name) {
	const dot = name.lastIndexOf(".");
	return dot > 0 && MEDIA_EXTENSIONS.has(name.slice(dot + 1).toLowerCase());
}
function parentPath(path) {
	const parts = path ? path.split("/") : [];
	parts.pop();
	return parts.join("/");
}
function listError(err) {
	if (err instanceof ApiError && typeof err.detail === "object" && err.detail !== null) {
		const detail = err.detail;
		if (typeof detail.error === "string") {
			return { error: detail.error, message: typeof detail.message === "string" ? detail.message : "" };
		}
	}
	return { error: "failed", message: err instanceof Error ? err.message : "" };
}
function stateKindForError(error) {
	switch (error) {
		case "permission_denied":
			return "denied";
		case "unauthorized":
			return "unauthorized";
		case "unplugged":
			return "unplugged";
		case "timeout":
			return "timeout";
		case "not_found":
			return "notfound";
		default:
			return "failed";
	}
}
function makeSentinel() {
	const sentinel = document.createElement("li");
	sentinel.className = "dp-sentinel";
	sentinel.setAttribute("aria-hidden", "true");
	return sentinel;
}
function showState(kind) {
	if (!session) {
		return;
	}
	session.stateKind = kind;
	const stateEl = el("dp-state");
	const list = el("dp-list");
	const head = document.querySelector("#dp-list-wrap .dp-head");
	const more = el("dp-more");
	if (!stateEl || !list || !head || !more) {
		return;
	}
	closeLightbox();
	session.thumbs.reset();
	session.images = [];
	stateEl.textContent = "";
	const title = document.createElement("strong");
	const body = document.createElement("span");
	let action = null;
	switch (kind) {
		case "loading": {
			const spinner = document.createElement("div");
			spinner.className = "dp-spinner";
			spinner.setAttribute("aria-hidden", "true");
			stateEl.appendChild(spinner);
			title.textContent = "Reading folder…";
			body.textContent = "Asking the phone for this folder’s contents.";
			break;
		}
		case "empty":
			title.textContent = "This folder is empty";
			body.textContent = "Use Up or the path above to go elsewhere.";
			break;
		case "nomatch":
			title.textContent = "No match";
			body.textContent = "Nothing in this folder matches “" + (el("dp-filter")?.value ?? "") + "”.";
			break;
		case "denied":
			title.textContent = "Android doesn’t allow access to this folder";
			body.textContent =
				"Folders like Android/data are protected on Android 11+ and can’t be read over USB. Pick another folder.";
			action = { label: "Go up", act: "up" };
			break;
		case "unauthorized":
			title.textContent = "Phone not authorized";
			body.textContent = "Unlock the phone and accept the “Allow USB debugging?” prompt, then retry.";
			action = { label: "Retry", act: "retry" };
			break;
		case "unplugged":
			title.textContent = "Phone disconnected";
			body.textContent =
				"The cable was unplugged or the phone went to sleep. Your ticked items are kept — reconnect and retry.";
			action = { label: "Retry", act: "retry" };
			break;
		case "timeout":
			title.textContent = "The phone took too long to answer";
			body.textContent = "Try again, or pick a smaller folder.";
			action = { label: "Retry", act: "retry" };
			break;
		case "notfound":
			title.textContent = "This folder no longer exists";
			body.textContent = "It was moved or deleted on the phone.";
			action = { label: "Go up", act: "up" };
			break;
		default:
			title.textContent = "Could not read this folder";
			body.textContent = "Something went wrong while listing the phone.";
			action = { label: "Retry", act: "retry" };
	}
	stateEl.appendChild(title);
	stateEl.appendChild(body);
	if (action) {
		stateEl.appendChild(document.createElement("br"));
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn btn-secondary";
		btn.setAttribute("data-dp-act", action.act);
		btn.textContent = action.label;
		stateEl.appendChild(btn);
	}
	stateEl.hidden = false;
	list.hidden = true;
	head.hidden = true;
	more.hidden = true;
	const status = el("dp-device-status");
	status?.classList.toggle("connected", kind !== "unauthorized" && kind !== "unplugged");
}
function renderTrail() {
	const trail = el("dp-trail");
	if (!trail || !session) {
		return;
	}
	trail.textContent = "";
	const parts = session.cwd ? session.cwd.split("/") : [];
	const addCrumb = (label, path, current) => {
		let node;
		if (current) {
			node = document.createElement("span");
			node.className = "dp-trail-current";
			node.setAttribute("aria-current", "page");
		} else {
			const btn = document.createElement("button");
			btn.type = "button";
			btn.addEventListener("click", () => {
				void navigate(path);
			});
			node = btn;
		}
		node.textContent = label;
		trail.appendChild(node);
	};
	addCrumb(rootName(session.options.method), "", parts.length === 0);
	let acc = "";
	parts.forEach((part, index) => {
		acc = joinPath(acc, part);
		const sep = document.createElement("span");
		sep.className = "dp-sep";
		sep.setAttribute("aria-hidden", "true");
		sep.textContent = "›";
		trail.appendChild(sep);
		addCrumb(part, acc, index === parts.length - 1);
	});
	const up = el("btn-dp-up");
	if (up) {
		up.disabled = session.cwd === "";
	}
}
function updateFooter() {
	if (!session) {
		return;
	}
	const count = session.selected.size;
	const countEl = el("dp-count");
	const add = el("btn-dp-add");
	const hint = el("dp-hint");
	if (countEl) {
		countEl.textContent =
			count === 0 ? "Nothing selected" : count + (count === 1 ? " item selected" : " items selected");
	}
	if (add) {
		add.disabled = count === 0;
		add.textContent = count === 0 ? "Add" : "Add " + count + (count === 1 ? " item" : " items");
	}
	if (hint) {
		const hasFolder = [...session.selected.values()].some((item) => item.isDir);
		hint.textContent = hasFolder
			? "Ticked folders are added whole (including sub-folders) when the transfer starts."
			: "";
	}
}
function makeRow(entry) {
	const active = session;
	const { kind, mediaOnly } = active.options;
	const path = joinPath(active.cwd, entry.name);
	const li = document.createElement("li");
	li.className =
		"dp-row" +
		(entry.name.startsWith(".") ? " is-hidden-file" : "") +
		(active.selected.has(path) ? " is-selected" : "");
	const box = document.createElement("input");
	box.type = "checkbox";
	box.checked = active.selected.has(path);
	box.setAttribute("aria-label", "Select " + entry.name);
	box.disabled = (kind === "folders" && !entry.is_dir) || (kind === "files" && entry.is_dir);
	box.addEventListener("change", () => {
		if (!session) {
			return;
		}
		if (box.checked) {
			session.selected.set(path, { path, isDir: entry.is_dir });
		} else {
			session.selected.delete(path);
		}
		li.classList.toggle("is-selected", box.checked);
		updateFooter();
		syncLightboxSelection();
	});
	let name;
	if (entry.is_dir) {
		const btn = document.createElement("button");
		btn.type = "button";
		btn.addEventListener("click", () => {
			void navigate(path);
		});
		name = btn;
	} else {
		name = document.createElement("span");
		if (mediaOnly && !isMediaName(entry.name)) {
			li.style.opacity = "0.55";
		}
	}
	name.className = "dp-name";
	const label = document.createElement("span");
	label.className = "dp-label";
	label.textContent = entry.name;
	const isVideo = !entry.is_dir && isPreviewableVideo(entry.name);
	const isImage = !entry.is_dir && (isImageName(entry.name) || isVideo);
	let thumb = null;
	let eye = null;
	if (isImage) {
		thumb = makeThumb(entry.name, isVideo);
		name.appendChild(thumb);
		name.appendChild(label);
		eye = document.createElement("button");
		eye.type = "button";
		eye.className = "dp-preview-btn";
		eye.textContent = "👁";
		eye.setAttribute("aria-label", "Preview " + entry.name + (isVideo ? " (video)" : ""));
		name.appendChild(eye);
	} else {
		const icon = document.createElement("span");
		icon.className = "dp-ico" + (!entry.is_dir && isVideoName(entry.name) ? " dp-ico-media" : "");
		icon.setAttribute("aria-hidden", "true");
		icon.textContent = entry.is_dir ? "📁" : isVideoName(entry.name) ? "🎞" : "📄";
		name.appendChild(icon);
		name.appendChild(label);
	}
	const size = document.createElement("span");
	size.className = "dp-size";
	size.textContent = entry.is_dir ? "—" : formatSize(entry.size);
	const date = document.createElement("span");
	date.className = "dp-date";
	date.textContent = formatDate(entry.mtime);
	li.appendChild(box);
	li.appendChild(name);
	li.appendChild(size);
	li.appendChild(date);
	if (thumb && eye) {
		wireImageRow(active, li, box, entry, path, thumb, eye);
	}
	return li;
}
function makeThumb(name, video) {
	const thumb = document.createElement("button");
	thumb.type = "button";
	thumb.className = "dp-thumb" + (video ? " dp-thumb-video" : "") + " is-loading";
	thumb.setAttribute("aria-label", "Preview " + name + (video ? " (video)" : ""));
	const img = document.createElement("span");
	img.className = "dp-thumb-img";
	const glyph = document.createElement("span");
	glyph.className = "dp-thumb-glyph";
	glyph.setAttribute("aria-hidden", "true");
	glyph.textContent = video ? "🎞" : "🖼";
	thumb.appendChild(img);
	thumb.appendChild(glyph);
	if (video) {
		const play = document.createElement("span");
		play.className = "dp-thumb-play";
		play.setAttribute("aria-hidden", "true");
		play.textContent = "▶";
		const dur = document.createElement("span");
		dur.className = "dp-thumb-dur";
		dur.setAttribute("aria-hidden", "true");
		thumb.appendChild(play);
		thumb.appendChild(dur);
	}
	return thumb;
}
/** Register the row for lazy thumbnails and lightbox browsing; the openers never touch ticks or folders. */
function wireImageRow(active, li, box, entry, path, thumb, eye) {
	const { method, deviceId } = active.options;
	const target = { method, deviceId, path, size: entry.size, mtime: entry.mtime };
	const video = thumb.classList.contains("dp-thumb-video");
	active.thumbs.register(thumb, target, (duration) => {
		const text = duration === null ? "" : formatMediaDuration(duration);
		const suffix = !video ? "" : text ? " (video, " + text + ")" : " (video)";
		eye.setAttribute("aria-label", "Preview " + entry.name + suffix);
	});
	active.images.push({
		path,
		name: entry.name,
		info: formatSize(entry.size) + " · " + formatDate(entry.mtime),
		target,
		thumbUrl: () => active.thumbs.objectUrlFor(thumb),
		kind: video ? "video" : "image",
		durationSeconds: () => active.thumbs.durationFor(thumb),
		isSelected: () => box.checked,
		setSelected: (selected) => {
			if (!box.disabled && box.checked !== selected) {
				box.checked = selected;
				box.dispatchEvent(new Event("change"));
			}
		},
	});
	for (const opener of [thumb, eye]) {
		opener.addEventListener("click", (ev) => {
			ev.stopPropagation();
			openLightbox(path, opener);
		});
	}
	li.dataset.path = path;
}
function clearTail() {
	if (session?.tail) {
		session.tail.remove();
		session.tail = null;
	}
}
function setTail(kind) {
	clearTail();
	const list = el("dp-list");
	if (!session || !kind || !list) {
		return;
	}
	const tail = document.createElement("li");
	tail.className = "dp-tail-row" + (kind === "error" ? " is-error" : "");
	if (kind === "loading") {
		tail.setAttribute("role", "status");
		const spinner = document.createElement("span");
		spinner.className = "dp-spinner";
		spinner.setAttribute("aria-hidden", "true");
		const text = document.createElement("span");
		text.textContent = "Loading more…";
		tail.appendChild(spinner);
		tail.appendChild(text);
	} else {
		tail.setAttribute("role", "alert");
		const text = document.createElement("span");
		text.textContent = "Couldn’t load more items.";
		const retry = document.createElement("button");
		retry.type = "button";
		retry.className = "btn btn-secondary";
		retry.setAttribute("data-dp-tail", "retry");
		retry.textContent = "Retry";
		retry.addEventListener("click", () => {
			void loadNext(true);
		});
		tail.appendChild(text);
		tail.appendChild(retry);
	}
	session.tail = tail;
	list.appendChild(tail);
}
function disconnectObserver() {
	if (session?.observer) {
		session.observer.disconnect();
		session.observer = null;
	}
}
function ensureObserver(list) {
	if (!session) {
		return null;
	}
	if (!session.observer && typeof IntersectionObserver !== "undefined") {
		session.observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					void loadNext(false);
				}
			},
			{ root: list, rootMargin: "0px 0px 120px 0px" },
		);
	}
	return session.observer;
}
/** Keep the sentinel as the last child while more pages exist; re-observe so it fires even if still in view. */
function placeSentinel() {
	const list = el("dp-list");
	if (!session || !list) {
		return;
	}
	const { sentinel } = session;
	session.observer?.unobserve(sentinel);
	if (session.nextCursor === null) {
		sentinel.remove();
		return;
	}
	list.appendChild(sentinel);
	if (!session.loadError) {
		ensureObserver(list)?.observe(sentinel);
	}
}
function updateMore() {
	const more = el("dp-more");
	const moreText = el("dp-more-text");
	const btn = el("btn-dp-more");
	const list = el("dp-list");
	if (!session || !more || !moreText || !list) {
		return;
	}
	more.hidden = session.nextCursor === null || list.hidden;
	moreText.textContent =
		"Showing " + session.loaded.toLocaleString("en-US") + " of " + session.total.toLocaleString("en-US") + " items";
	if (btn) {
		btn.disabled = session.loadingMore;
	}
}
function currentQuery() {
	return (el("dp-filter")?.value ?? "").trim().slice(0, 200);
}
async function fetchPage(cursor, refresh) {
	if (!session) {
		throw new Error("picker closed");
	}
	const { method, deviceId } = session.options;
	const body = {
		method,
		device_id: deviceId,
		path: session.cwd,
		cursor,
		limit: PAGE_SIZE,
		show_hidden: !!el("dp-hidden-toggle")?.checked,
	};
	const query = currentQuery();
	if (query) {
		body.query = query;
	}
	if (session.sort) {
		body.sort = session.sort.key;
		body.order = session.sort.order;
	}
	if (refresh) {
		body.refresh = true;
	}
	return apiSend("POST", "/api/device/list", body);
}
function isSortKey(value) {
	return value === "name" || value === "mtime" || value === "size";
}
function isSortOrder(value) {
	return value === "asc" || value === "desc";
}
function sortLabel(sort) {
	return SORT_LABEL[sort.key + ":" + sort.order] ?? "";
}
function renderSort() {
	const active = session?.sort ?? null;
	const select = el("dp-sort-select");
	if (select && active) {
		select.value = active.key + ":" + active.order;
	}
	for (const button of document.querySelectorAll("[data-dp-sort]")) {
		const key = button.getAttribute("data-dp-sort");
		const isActive = active !== null && active.key === key;
		button.classList.toggle("is-active", isActive);
		const arrow = button.querySelector(".dp-sort-arrow");
		if (arrow) {
			arrow.textContent = isActive ? (active.order === "asc" ? "▲" : "▼") : "";
		}
		const next = isActive ? (active.order === "asc" ? "desc" : "asc") : SORT_NATURAL_ORDER[key];
		const nextLabel = (SORT_LABEL[key + ":" + next] ?? "").toLowerCase();
		button.setAttribute(
			"aria-label",
			COLUMN_LABEL[key] + (isActive ? ", sorted " + sortLabel(active).toLowerCase() : "") + ". Sort " + nextLabel + ".",
		);
	}
}
/** Sort change: same restart as the hidden toggle (dimmed list, page 1, ticks and filter kept). */
function setSort(key, order) {
	if (!session) {
		return;
	}
	if (session.sort?.key === key && session.sort.order === order) {
		return;
	}
	session.sort = { key, order };
	renderSort();
	const status = el("dp-sort-status");
	if (status) {
		status.textContent = "Sorted " + sortLabel(session.sort).toLowerCase() + ". Folders stay first.";
	}
	if (session.filterTimer !== null) {
		window.clearTimeout(session.filterTimer);
		session.filterTimer = null;
	}
	void startListing(!!el("dp-list")?.hidden, false);
}
function renderFirstPage(page) {
	const list = el("dp-list");
	const stateEl = el("dp-state");
	const head = document.querySelector("#dp-list-wrap .dp-head");
	if (!session || !list || !stateEl || !head) {
		return;
	}
	renderTrail();
	if (page.sort && page.order && isSortKey(page.sort) && isSortOrder(page.order)) {
		session.sort = { key: page.sort, order: page.order };
	}
	renderSort();
	session.loaded = page.entries.length;
	session.total = page.total;
	session.nextCursor = page.next_cursor;
	if (page.entries.length === 0) {
		session.nextCursor = null;
		showState(currentQuery() ? "nomatch" : "empty");
		updateFooter();
		return;
	}
	session.stateKind = null;
	el("dp-device-status")?.classList.add("connected");
	stateEl.hidden = true;
	list.hidden = false;
	head.hidden = false;
	closeLightbox();
	session.thumbs.reset();
	session.images = [];
	list.textContent = "";
	session.tail = null;
	for (const entry of page.entries) {
		list.appendChild(makeRow(entry));
	}
	list.scrollTop = 0;
	placeSentinel();
	updateMore();
	updateFooter();
}
/** Restart at page 1 (open folder, filter, hidden toggle). `blank` swaps the list for the loading panel. */
async function startListing(blank, refresh) {
	if (!session) {
		return;
	}
	session.requestId += 1;
	const mine = session.requestId;
	session.loadingMore = false;
	session.loadError = false;
	session.nextCursor = null;
	session.observer?.unobserve(session.sentinel);
	session.thumbs.cancelPending();
	clearTail();
	const list = el("dp-list");
	renderTrail();
	if (blank) {
		list?.classList.remove("is-refreshing");
		showState("loading");
	} else {
		list?.classList.add("is-refreshing");
	}
	try {
		const page = await fetchPage(null, refresh);
		if (!session || session.requestId !== mine) {
			return;
		}
		list?.classList.remove("is-refreshing");
		renderFirstPage(page);
	} catch (err) {
		if (!session || session.requestId !== mine) {
			return;
		}
		list?.classList.remove("is-refreshing");
		renderTrail();
		showState(stateKindForError(listError(err).error));
	}
}
/** Next page: append rows only; never rebuild existing `<li>`s. */
async function loadNext(refresh) {
	const list = el("dp-list");
	if (!session || !list || session.loadingMore || session.nextCursor === null) {
		return;
	}
	const cursor = session.nextCursor;
	const mine = session.requestId;
	session.loadingMore = true;
	session.loadError = false;
	setTail("loading");
	placeSentinel();
	updateMore();
	try {
		const page = await fetchPage(cursor, refresh);
		if (!session || session.requestId !== mine) {
			return;
		}
		clearTail();
		for (const entry of page.entries) {
			list.appendChild(makeRow(entry));
		}
		session.loaded += page.entries.length;
		session.total = page.total;
		session.nextCursor = page.next_cursor;
		session.loadingMore = false;
		placeSentinel();
		updateMore();
	} catch (err) {
		if (!session || session.requestId !== mine) {
			return;
		}
		session.loadingMore = false;
		if (listError(err).error === "invalid_cursor") {
			void startListing(false, false);
			return;
		}
		session.loadError = true;
		setTail("error");
		placeSentinel();
		updateMore();
	}
}
async function navigate(path, refresh = false) {
	if (!session) {
		return;
	}
	session.cwd = path;
	session.total = 0;
	session.loaded = 0;
	if (session.filterTimer !== null) {
		window.clearTimeout(session.filterTimer);
		session.filterTimer = null;
	}
	disconnectObserver();
	const filter = el("dp-filter");
	if (filter) {
		filter.value = "";
	}
	await startListing(true, refresh);
}
function finish(commit) {
	const current = session;
	if (!current) {
		return;
	}
	if (current.filterTimer !== null) {
		window.clearTimeout(current.filterTimer);
	}
	current.observer?.disconnect();
	closeLightbox();
	current.thumbs.reset();
	session = null;
	showView(current.options.origin, { skipHistory: true });
	if (commit) {
		current.options.onAdd([...current.selected.values()]);
	}
}
/** Open the in-app phone browser. `onAdd` receives the ticked storage-relative paths when the user confirms. */
function openDevicePicker(options) {
	session = {
		options,
		cwd: "",
		loaded: 0,
		total: 0,
		nextCursor: null,
		selected: new Map(),
		requestId: 0,
		stateKind: null,
		loadingMore: false,
		loadError: false,
		observer: null,
		sentinel: makeSentinel(),
		tail: null,
		filterTimer: null,
		sort: null,
		thumbs: createThumbLoader(el("dp-list")),
		images: [],
	};
	renderSort();
	const origin = el("dp-bc-origin");
	if (origin) {
		origin.textContent = options.originLabel;
	}
	const title = el("dp-bc-title");
	if (title) {
		title.textContent = options.kind === "folders" ? "Pick folders" : "Pick files";
	}
	const heading = el("dp-title");
	if (heading) {
		heading.textContent = rootName(options.method);
	}
	const status = el("dp-device-status-text");
	if (status) {
		status.textContent =
			(options.deviceLabel || "Device") + " · Connected via " + (options.method === "afc" ? "iPhone USB" : "ADB");
	}
	const note = el("dp-media-note");
	if (note) {
		note.hidden = !options.mediaOnly;
	}
	const selectFolder = el("btn-dp-select-folder");
	if (selectFolder) {
		selectFolder.hidden = options.kind === "files";
	}
	const hiddenToggle = el("dp-hidden-toggle");
	if (hiddenToggle) {
		hiddenToggle.checked = false;
	}
	bindLightbox({
		items: () => session?.images ?? [],
		selectionDisabled: () => session?.options.kind === "folders",
	});
	showView("device-picker", { skipHistory: true });
	updateFooter();
	void navigate("");
}
function bindDevicePicker() {
	onClick("dp-bc-origin", () => {
		finish(false);
	});
	onClick("btn-dp-cancel", () => {
		finish(false);
	});
	onClick("btn-dp-add", () => {
		finish(true);
	});
	onClick("btn-dp-up", () => {
		if (session) {
			void navigate(parentPath(session.cwd));
		}
	});
	onClick("btn-dp-select-folder", () => {
		if (!session?.cwd) {
			return;
		}
		session.selected.set(session.cwd, { path: session.cwd, isDir: true });
		const hint = el("dp-hint");
		const name = session.cwd.split("/").pop() ?? session.cwd;
		updateFooter();
		if (hint) {
			hint.textContent = "Added “" + name + "” as a whole folder.";
		}
	});
	el("dp-hidden-toggle")?.addEventListener("change", () => {
		if (!session) {
			return;
		}
		if (session.filterTimer !== null) {
			window.clearTimeout(session.filterTimer);
			session.filterTimer = null;
		}
		void startListing(false, false);
	});
	for (const button of document.querySelectorAll("[data-dp-sort]")) {
		button.addEventListener("click", () => {
			if (!session) {
				return;
			}
			const key = button.getAttribute("data-dp-sort");
			const current = session.sort ?? { key: "name", order: "asc" };
			const order = current.key === key ? (current.order === "asc" ? "desc" : "asc") : SORT_NATURAL_ORDER[key];
			setSort(key, order);
		});
	}
	el("dp-sort-select")?.addEventListener("change", (ev) => {
		const [key, order] = ev.target.value.split(":");
		setSort(key, order);
	});
	el("dp-filter")?.addEventListener("input", () => {
		if (!session) {
			return;
		}
		if (session.filterTimer !== null) {
			window.clearTimeout(session.filterTimer);
		}
		session.filterTimer = window.setTimeout(() => {
			if (session) {
				session.filterTimer = null;
				void startListing(false, false);
			}
		}, FILTER_DEBOUNCE_MS);
	});
	onClick("btn-dp-more", () => {
		void loadNext(!!session?.loadError);
	});
	el("dp-state")?.addEventListener("click", (ev) => {
		const target = ev.target;
		const act = target instanceof Element ? target.getAttribute("data-dp-act") : null;
		if (!session || !act) {
			return;
		}
		void navigate(act === "up" ? parentPath(session.cwd) : session.cwd, act === "retry");
	});
}

export { bindDevicePicker, formatSize, isMediaName, openDevicePicker, parentPath };
