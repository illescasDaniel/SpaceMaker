// Phone picker layout (List / Grid): pure resolution logic, no DOM.
// Resolution order (spec device-file-picker → Grid view): the user's stored choice for the folder, then the
// folder type reported by the server (`folder_view`), then auto-detection from the page-1 counts.
/** Stored choice, else folder type, else detection (Grid when `mediaCount >= 1` and `mediaCount >= 0.6 * entryCount`). */
function resolveView(hints, counts) {
	if (hints.storedView) return { mode: hints.storedView, reason: "stored" };
	if (hints.folderView) return { mode: hints.folderView, reason: "folder" };
	// Integer maths: media >= 0.6 * entries  <=>  media * 5 >= entries * 3 (no float rounding at exactly 60 %).
	const grid = counts.mediaCount >= 1 && counts.mediaCount * 5 >= counts.entryCount * 3;
	return { mode: grid ? "grid" : "list", reason: "detected" };
}
/** Text of the Auto note; `""` when the reason is `stored` (the "Only this folder" hint is shown instead). */
function autoNote(resolved) {
	if (resolved.reason === "stored") return "";
	const label = resolved.mode === "grid" ? "Grid" : "List";
	if (resolved.reason === "detected") return `Auto \u00b7 ${label}`;
	return `Auto \u00b7 ${label} (${resolved.mode === "grid" ? "photo" : "documents"} folder)`;
}
function asMode(value) {
	return value === "list" || value === "grid" ? value : null;
}
function asCount(value) {
	return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}
/** Read `folder_view`, `stored_view`, `entry_count`, `media_count` from a list response (or an error `detail`). */
function parseViewFields(json) {
	if (typeof json !== "object" || json === null || Array.isArray(json)) {
		return { hints: { folderView: null, storedView: null }, counts: null };
	}
	const o = json;
	const entryCount = asCount(o["entry_count"]);
	const mediaCount = asCount(o["media_count"]);
	return {
		hints: { folderView: asMode(o["folder_view"]), storedView: asMode(o["stored_view"]) },
		counts: entryCount !== null && mediaCount !== null ? { entryCount, mediaCount } : null,
	};
}

export { autoNote, parseViewFields, resolveView };
