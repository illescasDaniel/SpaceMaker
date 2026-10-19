import { beforeEach, describe, expect, it, vi } from "vitest";
import { S } from "../src/state.ts";
import type { AppSnapshot } from "../src/types.ts";
import { bindUsbDestination, isAbsoluteDestination, updateUsbTransferUi } from "../src/usb.ts";

describe("isAbsoluteDestination", () => {
	it("given posix, drive-letter and UNC paths then they are absolute", () => {
		expect(isAbsoluteDestination("/home/u/Backups")).toBe(true);
		expect(isAbsoluteDestination("C:\\Users\\u")).toBe(true);
		expect(isAbsoluteDestination("\\\\server\\share")).toBe(true);
	});

	it("given relative or empty text then it is not absolute", () => {
		expect(isAbsoluteDestination("Backups/phone")).toBe(false);
		expect(isAbsoluteDestination("  ")).toBe(false);
	});
});

const MARKUP = `
<section id="view-usb-file-transfer">
	<div id="uft-form-banner" hidden></div>
	<input id="uft-dest-path" />
	<button id="btn-uft-dest-browse"></button>
	<button id="btn-uft-dest-reset" hidden></button>
	<p id="uft-dest-error" hidden></p>
	<button id="btn-uft-start"></button>
</section>`;

function snapshot(overrides: Record<string, unknown> = {}): AppSnapshot {
	return {
		active_module: "usb_file_transfer",
		connection_method: "adb",
		usb_transfer: { phase: "idle", progress: { completed: 0, total: 0, percent: 0 } },
		usb_transfer_actions: { start: true },
		usb_transfer_destination: "/home/u/SpaceMaker",
		usb_transfer_destination_custom: true,
		...overrides,
	} as unknown as AppSnapshot;
}

function input(): HTMLInputElement {
	return document.getElementById("uft-dest-path") as HTMLInputElement;
}

beforeEach(() => {
	document.body.innerHTML = MARKUP;
	globalThis.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify({}), { status: 200 }))) as typeof fetch;
	S.uftFoldersMethod = "adb";
	S.uftAvailableFoldersKey = "all";
	(window as unknown as { pywebview?: unknown }).pywebview = undefined;
	bindUsbDestination();
});

describe("destination row", () => {
	it("given a transfer is running then field, Browse and Use default are disabled", () => {
		// given
		const running = snapshot({ usb_transfer: { phase: "running", progress: { completed: 1, total: 4, percent: 25 } } });
		// when
		updateUsbTransferUi(running);
		// then
		expect(input().disabled).toBe(true);
		expect((document.getElementById("btn-uft-dest-browse") as HTMLButtonElement).disabled).toBe(true);
		expect((document.getElementById("btn-uft-dest-reset") as HTMLButtonElement).disabled).toBe(true);
	});

	it("given no transfer is running then the controls are enabled and Use default shows for a custom folder", () => {
		// given
		// when
		updateUsbTransferUi(snapshot());
		// then
		expect(input().disabled).toBe(false);
		expect(input().value).toBe("/home/u/SpaceMaker");
		expect((document.getElementById("btn-uft-dest-reset") as HTMLButtonElement).hidden).toBe(false);
	});

	it("given the desktop shell is missing when Browse is clicked then a banner explains and nothing is stored", () => {
		// given
		input().value = "/old";
		// when
		(document.getElementById("btn-uft-dest-browse") as HTMLButtonElement).click();
		// then
		const banner = document.getElementById("uft-form-banner") as HTMLElement;
		expect(banner.hidden).toBe(false);
		expect(banner.textContent).toContain("Browse works in the desktop app");
		expect(input().value).toBe("/old");
		expect(globalThis.fetch).not.toHaveBeenCalled();
	});

	it("given a relative path is typed then the error shows and Start is disabled", () => {
		// given
		updateUsbTransferUi(snapshot());
		// when
		input().value = "Backups/phone";
		input().dispatchEvent(new Event("input"));
		input().dispatchEvent(new Event("change"));
		// then
		expect((document.getElementById("uft-dest-error") as HTMLElement).hidden).toBe(false);
		expect(input().getAttribute("aria-invalid")).toBe("true");
		expect((document.getElementById("btn-uft-start") as HTMLButtonElement).disabled).toBe(true);
		expect(globalThis.fetch).not.toHaveBeenCalled();
	});

	it("given an absolute path is typed then it is sent to settings", () => {
		// given
		// when
		input().value = "/home/u/Phone";
		input().dispatchEvent(new Event("change"));
		// then
		const sent = (globalThis.fetch as unknown as { mock: { calls: [string, RequestInit][] } }).mock.calls[0];
		expect(JSON.parse(String(sent[1].body)).usb_transfer_destination).toBe("/home/u/Phone");
	});
});
