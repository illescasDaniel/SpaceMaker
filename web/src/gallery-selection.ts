/** Select-mode state for the Gallery (spec: gallery-batch). Kept free of DOM and of other gallery
 * modules so the tile builders and the batch UI can both import it without a cycle. */

/** Mirrors `MAX_GALLERY_BATCH_ITEMS` in `spacemaker.domain.gallery_batch`; the server enforces it too. */
const MAX_GALLERY_BATCH_ITEMS = 500;

const selected = new Set<string>();
const listeners: Array<() => void> = [];
let selecting = false;

function notify(): void {
	for (const listener of listeners) {
		listener();
	}
}
function onSelectionChange(listener: () => void): void {
	listeners.push(listener);
}
function isSelecting(): boolean {
	return selecting;
}
/** Leaving select mode always clears the selection. */
function setSelecting(on: boolean): void {
	if (selecting === on) {
		return;
	}
	selecting = on;
	if (!on) {
		selected.clear();
	}
	notify();
}
function resetSelection(): void {
	const changed = selecting || selected.size > 0;
	selecting = false;
	selected.clear();
	if (changed) {
		notify();
	}
}
function isSelected(relativePath: string): boolean {
	return selected.has(relativePath);
}
function selectedPaths(): string[] {
	return Array.from(selected);
}
function selectedCount(): number {
	return selected.size;
}
function isOverLimit(): boolean {
	return selected.size > MAX_GALLERY_BATCH_ITEMS;
}
/** Actions need at least one item and at most `MAX_GALLERY_BATCH_ITEMS`. */
function batchActionsEnabled(): boolean {
	return selected.size > 0 && !isOverLimit();
}
function toggleSelected(relativePath: string): boolean {
	const now = !selected.has(relativePath);
	if (now) {
		selected.add(relativePath);
	} else {
		selected.delete(relativePath);
	}
	notify();
	return now;
}
function deselect(paths: readonly string[]): void {
	for (const path of paths) {
		selected.delete(path);
	}
	notify();
}
/** Per-month Select pill: selects every loaded path, or deselects them when all are already selected. */
function toggleGroup(paths: readonly string[]): void {
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
