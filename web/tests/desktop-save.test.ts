import { afterEach, describe, expect, it, vi } from "vitest";
import { canSaveOnDesktop, saveOnDesktop } from "../src/desktop-save.ts";

function handlers() {
	return { onProgress: vi.fn(), onDone: vi.fn(), onError: vi.fn() };
}

afterEach(() => {
	delete window.pywebview;
	vi.useRealTimers();
});

describe("desktop save", () => {
	it("given no bridge when checked then it is unavailable and nothing starts", async () => {
		const h = handlers();
		expect(canSaveOnDesktop()).toBe(false);
		expect(await saveOnDesktop("/x", "a.zip", h)).toBe(false);
	});

	it("given a cancelled dialog when saving then it resolves false without progress", async () => {
		window.pywebview = { api: { save_download: () => "", download_progress: vi.fn() } };
		const h = handlers();
		expect(await saveOnDesktop("/x", "a.zip", h)).toBe(false);
		expect(h.onProgress).not.toHaveBeenCalled();
	});

	it("given a finished download when saving then onDone receives the path", async () => {
		const progress = { downloaded: 1, total: 1, percent: 100, done: true, error: "", path: "/home/u/a.zip" };
		window.pywebview = { api: { save_download: () => "id1", download_progress: () => progress } };
		const h = handlers();
		expect(await saveOnDesktop("/x", "a.zip", h)).toBe(true);
		expect(h.onDone).toHaveBeenCalledWith("/home/u/a.zip");
		expect(h.onError).not.toHaveBeenCalled();
	});

	it("given a failed download when saving then onError receives the message", async () => {
		const progress = { downloaded: 0, total: 0, percent: 0, done: true, error: "disk full", path: "" };
		window.pywebview = { api: { save_download: () => "id1", download_progress: () => progress } };
		const h = handlers();
		await saveOnDesktop("/x", "a.zip", h);
		expect(h.onError).toHaveBeenCalledWith("disk full");
	});
});
