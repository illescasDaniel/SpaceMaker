// Phone picker: the View control (Auto / List / Grid) and the layout it drives.
// The grid is the same `<ul id="dp-list">` and `<li class="dp-row">` items as the list, laid out by CSS
// (`.dp-list.is-grid`, `#dp-card[data-view]`), so a mode switch only toggles classes: no request, no rebuilt rows,
// ticks and already-loaded thumbnails stay.

import { apiSend } from "./api.ts";
import {
	autoNote,
	type FolderCounts,
	parseViewFields,
	type ResolvedView,
	resolveView,
	type ViewHints,
	type ViewMode,
	type ViewSetting,
} from "./device-view.ts";

interface ViewState {
	pref: ViewSetting;
	hints: ViewHints;
	/** Counts of page 1 of the current open (filter / sort / hidden restarts never replace them). */
	counts: FolderCounts;
	resolved: ResolvedView;
}

const NO_COUNTS: FolderCounts = { entryCount: 0, mediaCount: 0 };

let state: ViewState = freshState();

/** Every View choice made in this page's lifetime (= this app run, which also spans closing and reopening the picker),
 * per folder path. `auto` is kept: it means "explicitly Auto" and overrides a stale `stored_view` from the server.
 * It is recorded on click, before and regardless of the PUT result, and wins over `stored_view` on every open. */
const sessionChoices = new Map<string, ViewSetting>();

function freshState(): ViewState {
	return {
		pref: "auto",
		hints: { folderView: null, storedView: null },
		counts: NO_COUNTS,
		resolved: { mode: "list", reason: "detected" },
	};
}

function el<T extends HTMLElement>(id: string): T | null {
	return document.getElementById(id) as T | null;
}

function radios(): HTMLButtonElement[] {
	return [...document.querySelectorAll<HTMLButtonElement>("#dp-view [data-dp-view]")];
}

function isGridActive(): boolean {
	return state.resolved.mode === "grid";
}

/** Toggle the layout classes, the radio states and the note / scope hint from `state`. */
function render(): void {
	const grid = isGridActive();
	for (const radio of radios()) {
		const on = radio.getAttribute("data-dp-view") === state.pref;
		radio.setAttribute("aria-checked", on ? "true" : "false");
		radio.tabIndex = on ? 0 : -1;
	}
	const note = el<HTMLElement>("dp-view-auto-note");
	if (note) {
		note.hidden = state.pref !== "auto";
		note.textContent = autoNote(state.resolved);
	}
	const scope = el<HTMLElement>("dp-view-scope");
	if (scope) {
		scope.hidden = state.pref === "auto";
	}
	el<HTMLElement>("dp-list")?.classList.toggle("is-grid", grid);
	const card = el<HTMLElement>("dp-card");
	if (card) {
		card.dataset["view"] = grid ? "grid" : "list";
	}
	syncTileLabels();
}

function setState(next: Partial<ViewState>): void {
	state = { ...state, ...next };
}

/** Pref shown by the control: the session choice, else the stored one, else Auto. */
function prefFor(path: string | null, hints: ViewHints): ViewSetting {
	return (path === null ? undefined : sessionChoices.get(path)) ?? hints.storedView ?? "auto";
}

/** Forget the choices of this app run (after the stored ones were cleared, so no stale session choice survives). */
function clearSessionChoices(): void {
	sessionChoices.clear();
}

/** The server's hints with this app run's choice for `path` laid over `storedView` (a session choice always wins). */
function withSessionChoice(path: string | null, hints: ViewHints): ViewHints {
	const chosen = path === null ? undefined : sessionChoices.get(path);
	return chosen === undefined ? hints : { ...hints, storedView: chosen === "auto" ? null : chosen };
}

/** Fresh picker session: nothing is known about any folder yet. */
function resetView(): void {
	state = freshState();
	render();
}

/** Page 1 of an open arrived: take the hints and counts, decide the layout once, apply it. */
function applyOpenPage(json: unknown, path: string): void {
	const parsed = parseViewFields(json);
	const hints = withSessionChoice(path, parsed.hints);
	const kept = parsed.counts ?? NO_COUNTS;
	setState({ pref: prefFor(path, hints), hints, counts: kept, resolved: resolveView(hints, kept) });
	render();
}

/** An open failed: the hints are inside the error `detail`, so the control still shows the stored choice. */
function applyOpenError(detail: unknown, path: string): void {
	const hints = withSessionChoice(path, parseViewFields(detail).hints);
	const decided = hints.storedView !== null || hints.folderView !== null;
	// Nothing to decide with (no stored choice, no folder type, no counts): keep the layout in effect.
	const resolved: ResolvedView = decided
		? resolveView(hints, NO_COUNTS)
		: { mode: state.resolved.mode, reason: "detected" };
	setState({ pref: prefFor(path, hints), hints, counts: NO_COUNTS, resolved });
	render();
}

/** Thumbnail label: "Preview <name>" in a list row; in a tile the thumbnail is the tile body, named by the file. */
function syncThumbLabel(thumb: HTMLElement): void {
	const eye = thumb.parentElement?.querySelector<HTMLElement>(".dp-preview-btn");
	const label = eye?.getAttribute("aria-label");
	if (!label) {
		return;
	}
	thumb.setAttribute("aria-label", isGridActive() ? label.replace(/^Preview /, "") : label);
}

function syncTileLabels(): void {
	for (const thumb of document.querySelectorAll<HTMLElement>("#dp-list .dp-thumb")) {
		syncThumbLabel(thumb);
	}
}

/** Keep the first visible item where it was while the rows change size. */
function withScrollAnchor(change: () => void): void {
	const list = el<HTMLElement>("dp-list");
	if (!list) {
		change();
		return;
	}
	const top = list.getBoundingClientRect().top;
	const anchor = [...list.children].find((child) => child.getBoundingClientRect().bottom > top);
	const before = anchor ? anchor.getBoundingClientRect().top - top : 0;
	change();
	if (anchor) {
		list.scrollTop += anchor.getBoundingClientRect().top - list.getBoundingClientRect().top - before;
	}
}

function announce(mode: ViewMode): void {
	const status = el<HTMLElement>("dp-sort-status");
	if (status) {
		status.textContent = mode === "grid" ? "Grid view" : "List view";
	}
}

/** Fire-and-forget: a failed write keeps the chosen mode for the session and shows nothing. */
function storeChoice(path: string, view: ViewSetting): void {
	apiSend("PUT", "/api/device/view", { path, view }).catch(() => undefined);
}

function choose(setting: ViewSetting, path: string | null): void {
	if (setting === state.pref) {
		return;
	}
	const before = state.resolved.mode;
	const hints: ViewHints = { ...state.hints, storedView: setting === "auto" ? null : setting };
	// Auto re-resolves from the folder type and the page-1 counts of this open; no list request.
	const resolved: ResolvedView = resolveView(hints, state.counts);
	setState({ pref: setting, hints, resolved });
	withScrollAnchor(render);
	if (path !== null) {
		sessionChoices.set(path, setting);
		storeChoice(path, setting);
	}
	if (state.resolved.mode !== before) {
		announce(state.resolved.mode);
	}
}

/** Wire the radiogroup. `currentPath` is the folder being shown (null when the picker is closed). */
function bindViewControl(currentPath: () => string | null): void {
	const buttons = radios();
	buttons.forEach((button, index) => {
		button.addEventListener("click", () => {
			choose(button.getAttribute("data-dp-view") as ViewSetting, currentPath());
		});
		button.addEventListener("keydown", (ev: KeyboardEvent) => {
			const step =
				ev.key === "ArrowRight" || ev.key === "ArrowDown" ? 1 : ev.key === "ArrowLeft" || ev.key === "ArrowUp" ? -1 : 0;
			if (step === 0) {
				return;
			}
			ev.preventDefault();
			const next = buttons[(index + step + buttons.length) % buttons.length];
			if (next) {
				next.focus();
				choose(next.getAttribute("data-dp-view") as ViewSetting, currentPath());
			}
		});
	});
}

export { applyOpenError, applyOpenPage, bindViewControl, clearSessionChoices, isGridActive, resetView, syncThumbLabel };
