import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	batchActionsEnabled,
	deselect,
	isOverLimit,
	isSelecting,
	MAX_GALLERY_BATCH_ITEMS,
	onSelectionChange,
	resetSelection,
	selectedCount,
	selectedPaths,
	setSelecting,
	toggleGroup,
	toggleSelected,
} from "../src/gallery-selection.ts";

beforeEach(() => {
	resetSelection();
});

describe("gallery selection", () => {
	it("given select mode on when a tile is toggled twice then it is selected and then cleared", () => {
		setSelecting(true);
		expect(toggleSelected("a.avif")).toBe(true);
		expect(selectedPaths()).toEqual(["a.avif"]);
		expect(toggleSelected("a.avif")).toBe(false);
		expect(selectedCount()).toBe(0);
	});

	it("given a partly selected month when group toggled then all are selected, and toggled again then all cleared", () => {
		setSelecting(true);
		toggleSelected("a.avif");
		toggleGroup(["a.avif", "b.avif"]);
		expect(selectedPaths().sort()).toEqual(["a.avif", "b.avif"]);
		toggleGroup(["a.avif", "b.avif"]);
		expect(selectedCount()).toBe(0);
	});

	it("given a selection when select mode is left then the selection is cleared", () => {
		setSelecting(true);
		toggleSelected("a.avif");
		setSelecting(false);
		expect(isSelecting()).toBe(false);
		expect(selectedCount()).toBe(0);
	});

	it("given more than the limit selected when checking then actions are disabled", () => {
		setSelecting(true);
		toggleGroup(Array.from({ length: MAX_GALLERY_BATCH_ITEMS + 1 }, (_, i) => `${i}.avif`));
		expect(isOverLimit()).toBe(true);
		expect(batchActionsEnabled()).toBe(false);
		deselect(["0.avif"]);
		expect(batchActionsEnabled()).toBe(true);
	});

	it("given a listener when the selection changes then it is notified", () => {
		const listener = vi.fn();
		onSelectionChange(listener);
		setSelecting(true);
		toggleSelected("a.avif");
		expect(listener).toHaveBeenCalled();
	});
});
