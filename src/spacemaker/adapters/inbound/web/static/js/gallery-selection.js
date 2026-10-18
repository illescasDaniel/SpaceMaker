/** Select-mode state for the Gallery (spec: gallery-batch). Kept free of DOM and of other gallery
 * modules so the tile builders and the batch UI can both import it without a cycle. */
/** Mirrors `MAX_GALLERY_BATCH_ITEMS` in `spacemaker.domain.gallery_batch`; the server enforces it too. */
const MAX_GALLERY_BATCH_ITEMS = 500;
const selected = new Set();
const listeners = [];
let selecting = false;
function notify() {
	for (const listener of listeners) {
		listener();
	}
}
function onSelectionChange(listener) {
	listeners.push(listener);
}
function isSelecting() {
	return selecting;
}
/** Leaving select mode always clears the selection. */
function setSelecting(on) {
	if (selecting === on) {
		return;
	}
	selecting = on;
	if (!on) {
		selected.clear();
	}
	notify();
}
function resetSelection() {
	const changed = selecting || selected.size > 0;
	selecting = false;
	selected.clear();
	if (changed) {
		notify();
	}
}
function isSelected(relativePath) {
	return selected.has(relativePath);
}
function selectedPaths() {
	return Array.from(selected);
}
function selectedCount() {
	return selected.size;
}
function isOverLimit() {
	return selected.size > MAX_GALLERY_BATCH_ITEMS;
}
/** Actions need at least one item and at most `MAX_GALLERY_BATCH_ITEMS`. */
function batchActionsEnabled() {
	return selected.size > 0 && !isOverLimit();
}
function toggleSelected(relativePath) {
	const now = !selected.has(relativePath);
	if (now) {
		selected.add(relativePath);
	} else {
		selected.delete(relativePath);
	}
	notify();
	return now;
}
function deselect(paths) {
	for (const path of paths) {
		selected.delete(path);
	}
	notify();
}
/** Per-month Select pill: selects every loaded path, or deselects them when all are already selected. */
function toggleGroup(paths) {
	const allSelected = paths.length > 0 && paths.every((path) => selected.has(path));
	for (const path of paths) {
		if (allSelected) {
			selected.delete(path);
		} else {
			selected.add(path);
		}
	}
	notify();
}

export {
	batchActionsEnabled,
	deselect,
	isOverLimit,
	isSelected,
	isSelecting,
	MAX_GALLERY_BATCH_ITEMS,
	onSelectionChange,
	resetSelection,
	selectedCount,
	selectedPaths,
	setSelecting,
	toggleGroup,
	toggleSelected,
};
