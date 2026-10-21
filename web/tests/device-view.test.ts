import { describe, expect, it } from "vitest";

import { autoNote, type FolderCounts, parseViewFields, resolveView, type ViewHints } from "../src/device-view.ts";

const NONE: ViewHints = { folderView: null, storedView: null };
const counts = (entryCount: number, mediaCount: number): FolderCounts => ({ entryCount, mediaCount });

describe("resolveView order", () => {
	it("uses the stored choice before the folder type and detection", () => {
		expect(resolveView({ folderView: "grid", storedView: "list" }, counts(10, 10))).toEqual({
			mode: "list",
			reason: "stored",
		});
		expect(resolveView({ folderView: "list", storedView: "grid" }, counts(10, 0))).toEqual({
			mode: "grid",
			reason: "stored",
		});
	});

	it("uses the folder type before detection (Documents/Trip with 50 photos is a list)", () => {
		expect(resolveView({ folderView: "list", storedView: null }, counts(50, 50))).toEqual({
			mode: "list",
			reason: "folder",
		});
	});

	it("opens a typed photo folder as a grid even when it holds no media (DCIM of folders)", () => {
		expect(resolveView({ folderView: "grid", storedView: null }, counts(5, 0))).toEqual({
			mode: "grid",
			reason: "folder",
		});
	});

	it("falls through to detection when neither a choice nor a type applies", () => {
		expect(resolveView(NONE, counts(4, 4))).toEqual({ mode: "grid", reason: "detected" });
	});
});

describe("resolveView detection", () => {
	it("is a grid for a folder of only media (Backup2024: 4 photos)", () => {
		expect(resolveView(NONE, counts(4, 4)).mode).toBe("grid");
	});

	it("is a grid for two screenshots and a single lonely photo (minimum is one and 60 %)", () => {
		expect(resolveView(NONE, counts(2, 2)).mode).toBe("grid");
		expect(resolveView(NONE, counts(1, 1)).mode).toBe("grid");
	});

	it("is a list for 3 photos among 10 entries (30 %)", () => {
		expect(resolveView(NONE, counts(10, 3)).mode).toBe("list");
	});

	it("is a list for one photo and one PDF (50 %)", () => {
		expect(resolveView(NONE, counts(2, 1)).mode).toBe("list");
	});

	it("is a grid exactly at 60 % and a list just under it", () => {
		expect(resolveView(NONE, counts(10, 6)).mode).toBe("grid");
		expect(resolveView(NONE, counts(10, 5)).mode).toBe("list");
		expect(resolveView(NONE, counts(5, 3)).mode).toBe("grid");
	});

	it("is a list for an empty folder and for a folder of only sub-folders", () => {
		expect(resolveView(NONE, counts(0, 0))).toEqual({ mode: "list", reason: "detected" });
		expect(resolveView(NONE, counts(7, 0))).toEqual({ mode: "list", reason: "detected" });
	});
});

describe("autoNote", () => {
	it("names the folder type when it decided", () => {
		expect(autoNote({ mode: "grid", reason: "folder" })).toBe("Auto · Grid (photo folder)");
		expect(autoNote({ mode: "list", reason: "folder" })).toBe("Auto · List (documents folder)");
	});

	it("is plain when detection decided", () => {
		expect(autoNote({ mode: "grid", reason: "detected" })).toBe("Auto · Grid");
		expect(autoNote({ mode: "list", reason: "detected" })).toBe("Auto · List");
	});

	it("is empty for a stored choice (the 'Only this folder' hint replaces it)", () => {
		expect(autoNote({ mode: "grid", reason: "stored" })).toBe("");
		expect(autoNote({ mode: "list", reason: "stored" })).toBe("");
	});

	it("matches what resolveView produced for the BDD folders", () => {
		expect(autoNote(resolveView({ folderView: "grid", storedView: null }, counts(3, 3)))).toBe(
			"Auto · Grid (photo folder)",
		);
		expect(autoNote(resolveView(NONE, counts(4, 4)))).toBe("Auto · Grid");
		expect(autoNote(resolveView(NONE, counts(10, 3)))).toBe("Auto · List");
	});
});

describe("parseViewFields", () => {
	it("reads page-1 fields", () => {
		expect(
			parseViewFields({ entry_count: 20, media_count: 10, folder_view: "grid", stored_view: "list", entries: [] }),
		).toEqual({
			hints: { folderView: "grid", storedView: "list" },
			counts: { entryCount: 20, mediaCount: 10 },
		});
	});

	it("maps null hints and keeps zero counts", () => {
		expect(parseViewFields({ entry_count: 0, media_count: 0, folder_view: null, stored_view: null })).toEqual({
			hints: NONE,
			counts: { entryCount: 0, mediaCount: 0 },
		});
	});

	it("returns no counts and empty hints for a cursor page without the fields", () => {
		expect(parseViewFields({ entries: [], next_cursor: null, total: 5 })).toEqual({ hints: NONE, counts: null });
	});

	it("keeps hints but no counts for an error detail", () => {
		expect(parseViewFields({ error: "unplugged", message: "", folder_view: "list", stored_view: "grid" })).toEqual({
			hints: { folderView: "list", storedView: "grid" },
			counts: null,
		});
	});

	it("ignores unknown view values instead of throwing", () => {
		expect(parseViewFields({ folder_view: "tiles", stored_view: "auto" }).hints).toEqual(NONE);
	});

	it("ignores counts that are not non-negative integers", () => {
		expect(parseViewFields({ entry_count: "3", media_count: 1 }).counts).toBeNull();
		expect(parseViewFields({ entry_count: 3 }).counts).toBeNull();
		expect(parseViewFields({ entry_count: -1, media_count: 0 }).counts).toBeNull();
	});

	it("never throws on non-objects", () => {
		for (const junk of [null, undefined, 5, "grid", []]) {
			expect(parseViewFields(junk)).toEqual({ hints: NONE, counts: null });
		}
	});
});
