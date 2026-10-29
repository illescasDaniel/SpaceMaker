import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bindLanDesktop, shouldShowDownloadAll, updateTransferUi } from "../src/lan.ts";
import type { AppSnapshot } from "../src/types.ts";

function snapshot(count: number): AppSnapshot {
	const items = Array.from({ length: count }, (_, i) => ({
		id: `f${i}`,
		name: `file${i}.txt`,
		kind: "file",
		origin: "phone",
	}));
	return { transfer_files_session: { active: true, items } } as unknown as AppSnapshot;
}

function button(): HTMLButtonElement {
	return document.getElementById("btn-transfer-download-all") as HTMLButtonElement;
}

describe("transfer download all", () => {
	beforeEach(() => {
		document.body.innerHTML = `
			<ul id="transfer-item-list"></ul>
			<p id="transfer-item-status"></p>
			<p id="transfer-save-tip" hidden><span id="transfer-save-tip-text"></span></p>
			<div id="transfer-save-actions" hidden></div>
			<button id="btn-transfer-download-all" hidden>Download all</button>`;
	});

	afterEach(() => {
		vi.restoreAllMocks();
		vi.unstubAllGlobals();
	});

	it("given counts when checked then the rule is two or more", () => {
		expect([0, 1, 2, 5].map(shouldShowDownloadAll)).toEqual([false, false, true, true]);
	});

	it("given zero or one item when the UI updates then the button is hidden", () => {
		// when
		updateTransferUi(snapshot(0));
		const hiddenAtZero = button().hidden;
		updateTransferUi(snapshot(1));
		// then
		expect(hiddenAtZero).toBe(true);
		expect(button().hidden).toBe(true);
	});

	it("given two items when the UI updates then the button shows, and hides again at one", () => {
		// when
		updateTransferUi(snapshot(2));
		const shownAtTwo = !button().hidden;
		updateTransferUi(snapshot(1));
		// then
		expect(shownAtTwo).toBe(true);
		expect(button().hidden).toBe(true);
	});

	it("given a click when the zip is saved then POST save-all runs and the tip shows", async () => {
		// given
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({ saved_path: "/d/z.zip", saved_name: "z.zip", saved_path_display: "Documents/SpaceMaker" }),
				{
					status: 200,
				},
			),
		);
		vi.stubGlobal("fetch", fetchMock);
		bindLanDesktop();
		updateTransferUi(snapshot(2));
		// when
		button().click();
		const disabledWhileRunning = button().disabled;
		await vi.waitFor(() => expect(button().disabled).toBe(false));
		// then
		expect(disabledWhileRunning).toBe(true);
		expect(fetchMock).toHaveBeenCalledWith("/api/transfer/save-all", expect.objectContaining({ method: "POST" }));
		expect(document.getElementById("transfer-save-tip")?.hidden).toBe(false);
		expect(document.getElementById("transfer-save-tip-text")?.textContent).toBe("Saved to Documents/SpaceMaker");
	});

	it("given a failing zip when clicked then it alerts and re-enables the button", async () => {
		// given
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 500 })),
		);
		const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);
		bindLanDesktop();
		updateTransferUi(snapshot(2));
		// when
		button().click();
		await vi.waitFor(() => expect(alertMock).toHaveBeenCalled());
		await vi.waitFor(() => expect(button().disabled).toBe(false));
		// then
		expect(alertMock).toHaveBeenCalledWith("boom");
		expect(document.getElementById("transfer-save-tip")?.hidden).toBe(true);
	});
});
