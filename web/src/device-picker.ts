import { ApiError, apiSend } from "./api.ts";
import { onClick } from "./dom.ts";
import { showView } from "./shell.ts";
import type {
	DeviceEntryRow,
	DeviceListError,
	DeviceListPage,
	DevicePickedItem,
	DevicePickerOptions,
	DevicePickerStateKind,
} from "./types.ts";

const MEDIA_EXTENSIONS: ReadonlySet<string> = new Set([
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

interface PickerSession {
	options: DevicePickerOptions;
	cwd: string;
	entries: DeviceEntryRow[];
	total: number;
	nextCursor: number | null;
	selected: Map<string, DevicePickedItem>;
	/** Bumped on every navigation so a slow listing for a folder we already left cannot render. */
	requestId: number;
	stateKind: DevicePickerStateKind | null;
}

let session: PickerSession | null = null;

function el<T extends HTMLElement>(id: string): T | null {
	return document.getElementById(id) as T | null;
}
function rootName(method: string): string {
	return method === "afc" ? "iPhone" : "Phone storage";
}
function joinPath(dir: string, name: string): string {
	return dir ? dir + "/" + name : name;
}
function formatSize(bytes: number): string {
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
function formatDate(epochSeconds: number): string {
	if (!epochSeconds) {
		return "";
	}
	const d = new Date(epochSeconds * 1000);
	const mm = String(d.getMonth() + 1).padStart(2, "0");
	const dd = String(d.getDate()).padStart(2, "0");
	return d.getFullYear() + "-" + mm + "-" + dd;
}
function isMediaName(name: string): boolean {
	const dot = name.lastIndexOf(".");
	return dot > 0 && MEDIA_EXTENSIONS.has(name.slice(dot + 1).toLowerCase());
}
function parentPath(path: string): string {
	const parts = path ? path.split("/") : [];
	parts.pop();
	return parts.join("/");
}
function listError(err: unknown): DeviceListError {
	if (err instanceof ApiError && typeof err.detail === "object" && err.detail !== null) {
		const detail = err.detail as { error?: unknown; message?: unknown };
		if (typeof detail.error === "string") {
			return { error: detail.error, message: typeof detail.message === "string" ? detail.message : "" };
		}
	}
	return { error: "failed", message: err instanceof Error ? err.message : "" };
}
function stateKindForError(error: string): DevicePickerStateKind {
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

function showState(kind: DevicePickerStateKind): void {
	if (!session) {
		return;
	}
	session.stateKind = kind;
	const stateEl = el<HTMLElement>("dp-state");
	const list = el<HTMLElement>("dp-list");
	const head = document.querySelector<HTMLElement>("#dp-list-wrap .dp-head");
	const more = el<HTMLElement>("dp-more");
	if (!stateEl || !list || !head || !more) {
		return;
	}
	stateEl.textContent = "";
	const title = document.createElement("strong");
	const body = document.createElement("span");
	let action: { label: string; act: string } | null = null;
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
			body.textContent = "Nothing in this folder matches “" + (el<HTMLInputElement>("dp-filter")?.value ?? "") + "”.";
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
	const status = el<HTMLElement>("dp-device-status");
	status?.classList.toggle("connected", kind !== "unauthorized" && kind !== "unplugged");
}

function renderTrail(): void {
	const trail = el<HTMLElement>("dp-trail");
	if (!trail || !session) {
		return;
	}
	trail.textContent = "";
	const parts = session.cwd ? session.cwd.split("/") : [];
	const addCrumb = (label: string, path: string, current: boolean): void => {
		let node: HTMLElement;
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
	const up = el<HTMLButtonElement>("btn-dp-up");
	if (up) {
		up.disabled = session.cwd === "";
	}
}

function visibleRows(): DeviceEntryRow[] {
	if (!session) {
		return [];
	}
	const showHidden = !!el<HTMLInputElement>("dp-hidden-toggle")?.checked;
	const query = (el<HTMLInputElement>("dp-filter")?.value ?? "").trim().toLowerCase();
	return session.entries.filter((entry) => {
		if (!showHidden && entry.name.startsWith(".")) {
			return false;
		}
		return !query || entry.name.toLowerCase().includes(query);
	});
}

function updateFooter(): void {
	if (!session) {
		return;
	}
	const count = session.selected.size;
	const countEl = el<HTMLElement>("dp-count");
	const add = el<HTMLButtonElement>("btn-dp-add");
	const hint = el<HTMLElement>("dp-hint");
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

function renderRows(): void {
	if (!session) {
		return;
	}
	const list = el<HTMLElement>("dp-list");
	const stateEl = el<HTMLElement>("dp-state");
	const head = document.querySelector<HTMLElement>("#dp-list-wrap .dp-head");
	const more = el<HTMLElement>("dp-more");
	const moreText = el<HTMLElement>("dp-more-text");
	if (!list || !stateEl || !head || !more || !moreText) {
		return;
	}
	renderTrail();
	const rows = visibleRows();
	if (rows.length === 0 && session.nextCursor === null) {
		const query = (el<HTMLInputElement>("dp-filter")?.value ?? "").trim();
		showState(query ? "nomatch" : "empty");
		updateFooter();
		return;
	}
	session.stateKind = null;
	el<HTMLElement>("dp-device-status")?.classList.add("connected");
	stateEl.hidden = true;
	list.hidden = false;
	head.hidden = false;
	list.textContent = "";
	const { kind, mediaOnly } = session.options;
	for (const entry of rows) {
		const path = joinPath(session.cwd, entry.name);
		const li = document.createElement("li");
		li.className =
			"dp-row" +
			(entry.name.startsWith(".") ? " is-hidden-file" : "") +
			(session.selected.has(path) ? " is-selected" : "");
		const box = document.createElement("input");
		box.type = "checkbox";
		box.checked = session.selected.has(path);
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
		});
		let name: HTMLElement;
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
		const icon = document.createElement("span");
		icon.className = "dp-ico";
		icon.setAttribute("aria-hidden", "true");
		icon.textContent = entry.is_dir ? "📁" : "📄";
		const label = document.createElement("span");
		label.className = "dp-label";
		label.textContent = entry.name;
		name.appendChild(icon);
		name.appendChild(label);
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
		list.appendChild(li);
	}
	if (session.nextCursor !== null) {
		more.hidden = false;
		moreText.textContent =
			"Showing " +
			session.entries.length.toLocaleString("en-US") +
			" of " +
			session.total.toLocaleString("en-US") +
			" items";
	} else {
		more.hidden = true;
	}
	updateFooter();
}

async function fetchPage(path: string, cursor: number): Promise<DeviceListPage> {
	if (!session) {
		throw new Error("picker closed");
	}
	const { method, deviceId } = session.options;
	return apiSend<DeviceListPage>("POST", "/api/device/list", { method, device_id: deviceId, path, cursor });
}

async function navigate(path: string): Promise<void> {
	if (!session) {
		return;
	}
	session.cwd = path;
	session.entries = [];
	session.total = 0;
	session.nextCursor = null;
	session.requestId += 1;
	const mine = session.requestId;
	const filter = el<HTMLInputElement>("dp-filter");
	if (filter) {
		filter.value = "";
	}
	renderTrail();
	showState("loading");
	try {
		const page = await fetchPage(path, 0);
		if (!session || session.requestId !== mine) {
			return;
		}
		session.entries = page.entries;
		session.total = page.total;
		session.nextCursor = page.next_cursor;
		renderRows();
	} catch (err) {
		if (!session || session.requestId !== mine) {
			return;
		}
		renderTrail();
		showState(stateKindForError(listError(err).error));
	}
}

async function loadMore(all: boolean): Promise<void> {
	if (!session || session.nextCursor === null) {
		return;
	}
	const mine = session.requestId;
	const btn = el<HTMLButtonElement>("btn-dp-more");
	if (btn) {
		btn.disabled = true;
	}
	try {
		while (session && session.requestId === mine && session.nextCursor !== null) {
			const page = await fetchPage(session.cwd, session.nextCursor);
			if (!session || session.requestId !== mine) {
				return;
			}
			session.entries = session.entries.concat(page.entries);
			session.total = page.total;
			session.nextCursor = page.next_cursor;
			if (!all) {
				break;
			}
		}
		renderRows();
	} catch (err) {
		if (session && session.requestId === mine) {
			showState(stateKindForError(listError(err).error));
		}
	} finally {
		if (btn) {
			btn.disabled = false;
		}
	}
}

function finish(commit: boolean): void {
	const current = session;
	session = null;
	if (!current) {
		return;
	}
	showView(current.options.origin, { skipHistory: true });
	if (commit) {
		current.options.onAdd([...current.selected.values()]);
	}
}

/** Open the in-app phone browser. `onAdd` receives the ticked storage-relative paths when the user confirms. */
function openDevicePicker(options: DevicePickerOptions): void {
	session = {
		options,
		cwd: "",
		entries: [],
		total: 0,
		nextCursor: null,
		selected: new Map(),
		requestId: 0,
		stateKind: null,
	};
	const origin = el<HTMLElement>("dp-bc-origin");
	if (origin) {
		origin.textContent = options.originLabel;
	}
	const title = el<HTMLElement>("dp-bc-title");
	if (title) {
		title.textContent = options.kind === "folders" ? "Pick folders" : "Pick files";
	}
	const heading = el<HTMLElement>("dp-title");
	if (heading) {
		heading.textContent = rootName(options.method);
	}
	const status = el<HTMLElement>("dp-device-status-text");
	if (status) {
		status.textContent =
			(options.deviceLabel || "Device") + " · Connected via " + (options.method === "afc" ? "iPhone USB" : "ADB");
	}
	const note = el<HTMLElement>("dp-media-note");
	if (note) {
		note.hidden = !options.mediaOnly;
	}
	const selectFolder = el<HTMLButtonElement>("btn-dp-select-folder");
	if (selectFolder) {
		selectFolder.hidden = options.kind === "files";
	}
	const hiddenToggle = el<HTMLInputElement>("dp-hidden-toggle");
	if (hiddenToggle) {
		hiddenToggle.checked = false;
	}
	showView("device-picker", { skipHistory: true });
	updateFooter();
	void navigate("");
}

function bindDevicePicker(): void {
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
		const hint = el<HTMLElement>("dp-hint");
		const name = session.cwd.split("/").pop() ?? session.cwd;
		renderRows();
		if (hint) {
			hint.textContent = "Added “" + name + "” as a whole folder.";
		}
	});
	el<HTMLInputElement>("dp-hidden-toggle")?.addEventListener("change", () => {
		renderRows();
	});
	el<HTMLInputElement>("dp-filter")?.addEventListener("input", () => {
		if (session?.nextCursor !== null && session && (el<HTMLInputElement>("dp-filter")?.value ?? "").trim()) {
			void loadMore(true);
			return;
		}
		renderRows();
	});
	onClick("btn-dp-more", () => {
		void loadMore(false);
	});
	el<HTMLElement>("dp-state")?.addEventListener("click", (ev: MouseEvent) => {
		const target = ev.target;
		const act = target instanceof Element ? target.getAttribute("data-dp-act") : null;
		if (!session || !act) {
			return;
		}
		void navigate(act === "up" ? parentPath(session.cwd) : session.cwd);
	});
}

export { bindDevicePicker, formatSize, isMediaName, openDevicePicker, parentPath };
