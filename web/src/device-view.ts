// Phone picker layout (List / Grid): pure resolution logic, no DOM.
// Resolution order (spec device-file-picker → Grid view): the user's stored choice for the folder, then the
// folder type reported by the server (`folder_view`), then auto-detection from the page-1 counts.

type ViewMode = "list" | "grid";
type ViewSetting = "auto" | ViewMode;

interface ViewHints {
	/** Layout the server's folder-type table gives for the path (`null` = no opinion). */
	folderView: ViewMode | null;
	/** The user's stored choice for exactly this path (`null` = Auto). */
	storedView: ViewMode | null;
}

interface FolderCounts {
	/** Folders + files after the hidden rule, ignoring the filter. */
	entryCount: number;
	/** Of those, files with a photo/video extension. */
	mediaCount: number;
}

type ViewReason = "stored" | "folder" | "detected";

interface ResolvedView {
	mode: ViewMode;
	reason: ViewReason;
}

interface ViewFields {
	hints: ViewHints;
	/** `null` when the response carries no counts (cursor pages, error responses). */
	counts: FolderCounts | null;
}

/** Stored choice, else folder type, else detection (Grid when `mediaCount >= 1` and `mediaCount >= 0.6 * entryCount`). */
function resolveView(hints: ViewHints, counts: FolderCounts): ResolvedView {
	if (hints.storedView) return { mode: hints.storedView, reason: "stored" };
	if (hints.folderView) return { mode: hints.folderView, reason: "folder" };
	// Integer maths: media >= 0.6 * entries  <=>  media * 5 >= entries * 3 (no float rounding at exactly 60 %).
	const grid = counts.mediaCount >= 1 && counts.mediaCount * 5 >= counts.entryCount * 3;
	return { mode: grid ? "grid" : "list", reason: "detected" };
}

/** Text of the Auto note; `""` when the reason is `stored` (the "Only this folder" hint is shown instead). */
function autoNote(resolved: ResolvedView): string {
	if (resolved.reason === "stored") return "";
	const label = resolved.mode === "grid" ? "Grid" : "List";
	if (resolved.reason === "detected") return `Auto \u00b7 ${label}`;
	return `Auto \u00b7 ${label} (${resolved.mode === "grid" ? "photo" : "documents"} folder)`;
}

function asMode(value: unknown): ViewMode | null {
	return value === "list" || value === "grid" ? value : null;
}

function asCount(value: unknown): number | null {
	return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

/** Read `folder_view`, `stored_view`, `entry_count`, `media_count` from a list response (or an error `detail`). */
function parseViewFields(json: unknown): ViewFields {
	if (typeof json !== "object" || json === null || Array.isArray(json)) {
		return { hints: { folderView: null, storedView: null }, counts: null };
	}
	const o = json as Record<string, unknown>;
	const entryCount = asCount(o["entry_count"]);
	const mediaCount = asCount(o["media_count"]);
	return {
		hints: { folderView: asMode(o["folder_view"]), storedView: asMode(o["stored_view"]) },
		counts: entryCount !== null && mediaCount !== null ? { entryCount, mediaCount } : null,
	};
}

export type { FolderCounts, ResolvedView, ViewFields, ViewHints, ViewMode, ViewReason, ViewSetting };
export { autoNote, parseViewFields, resolveView };
