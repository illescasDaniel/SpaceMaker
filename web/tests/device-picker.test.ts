import { beforeEach, describe, expect, it, vi } from "vitest";

const showView = vi.fn();
vi.mock("../src/shell.ts", () => ({ showView: (...args: unknown[]) => showView(...args), applyState: vi.fn() }));

import { bindDevicePicker, formatSize, isMediaName, openDevicePicker, parentPath } from "../src/device-picker.ts";
import type { DeviceListPage } from "../src/types.ts";

const MARKUP = `
<span id="dp-bc-origin"></span><span id="dp-bc-title"></span><h2 id="dp-title"></h2>
<span id="dp-device-status-text"></span><div id="dp-device-status"></div><div id="dp-media-note" hidden></div>
<nav id="dp-trail"></nav><button id="btn-dp-up"></button><button id="btn-dp-select-folder"></button>
<input id="dp-filter" /><input type="checkbox" id="dp-hidden-toggle" />
<div id="dp-list-wrap"><div class="dp-head"></div><ul id="dp-list"></ul><div id="dp-state" hidden></div>
<div id="dp-more" hidden><span id="dp-more-text"></span><button id="btn-dp-more"></button></div></div>
<p id="dp-hint"></p><span id="dp-count"></span><button id="btn-dp-cancel"></button><button id="btn-dp-add"></button>`;

function page(path: string, names: Array<[string, boolean]>, next: number | null = null): DeviceListPage {
	return {
		path,
		entries: names.map(([name, is_dir]) => ({ name, is_dir, size: 10, mtime: 0 })),
		next_cursor: next,
		total: names.length,
	};
}

function mockList(pages: Record<string, DeviceListPage | { status: number; detail: unknown }>): void {
	globalThis.fetch = vi.fn((_url: unknown, init?: RequestInit) => {
		const body = JSON.parse(String(init?.body)) as { path: string };
		const hit = pages[body.path];
		if (hit && "status" in hit) {
			return Promise.resolve(new Response(JSON.stringify({ detail: hit.detail }), { status: hit.status }));
		}
		return Promise.resolve(new Response(JSON.stringify(hit ?? page(body.path, [])), { status: 200 }));
	}) as typeof fetch;
}

const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));
let bound = false;

beforeEach(() => {
	document.body.innerHTML = MARKUP;
	showView.mockClear();
	bound = false;
});

function open(onAdd = vi.fn(), kind: "files" | "folders" = "files"): ReturnType<typeof vi.fn> {
	if (!bound) {
		bindDevicePicker();
		bound = true;
	}
	openDevicePicker({
		origin: "usb-file-transfer",
		originLabel: "USB file transfer",
		method: "adb",
		deviceId: "dev1",
		deviceLabel: "Pixel",
		kind,
		mediaOnly: false,
		onAdd,
	});
	return onAdd;
}

describe("device picker helpers", () => {
	it("formats sizes and detects media names", () => {
		expect(formatSize(512)).toBe("512 B");
		expect(formatSize(2048)).toBe("2 KB");
		expect(isMediaName("IMG_1.JPG")).toBe(true);
		expect(isMediaName("report.pdf")).toBe(false);
		expect(parentPath("a/b/c")).toBe("a/b");
		expect(parentPath("a")).toBe("");
	});
});

describe("device picker", () => {
	it("given awkward names when listed then they render as exact text, never markup", async () => {
		mockList({
			"": page("", [
				["<b>x</b>", false],
				["line\nbreak.txt", false],
			]),
		});
		open();
		await flush();
		const labels = [...document.querySelectorAll(".dp-label")].map((n) => n.textContent);
		expect(labels).toEqual(["<b>x</b>", "line\nbreak.txt"]);
		expect(document.querySelector("#dp-list b")).toBeNull();
	});

	it("given ticks in two folders when added then both reach the caller with storage-relative paths", async () => {
		mockList({
			"": page("", [
				["Download", true],
				["a.txt", false],
			]),
			Download: page("Download", [["report.pdf", false]]),
		});
		const onAdd = open();
		await flush();
		(document.querySelector("#dp-list input") as HTMLInputElement | null)?.dispatchEvent(new Event("change"));
		const boxes = document.querySelectorAll<HTMLInputElement>("#dp-list input");
		const fileBox = boxes[1] as HTMLInputElement;
		fileBox.checked = true;
		fileBox.dispatchEvent(new Event("change"));
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		const inner = document.querySelector("#dp-list input") as HTMLInputElement;
		inner.checked = true;
		inner.dispatchEvent(new Event("change"));
		(document.getElementById("btn-dp-add") as HTMLButtonElement).click();
		expect(onAdd).toHaveBeenCalledWith([
			{ path: "a.txt", isDir: false },
			{ path: "Download/report.pdf", isDir: false },
		]);
		expect(showView).toHaveBeenLastCalledWith("usb-file-transfer", { skipHistory: true });
	});

	it("given cancel then nothing is added", async () => {
		mockList({ "": page("", [["a.txt", false]]) });
		const onAdd = open();
		await flush();
		(document.getElementById("btn-dp-cancel") as HTMLButtonElement).click();
		expect(onAdd).not.toHaveBeenCalled();
	});

	it("given a protected folder when listed then the denied panel offers Go up", async () => {
		mockList({
			"": page("", [["Android", true]]),
			Android: { status: 403, detail: { error: "permission_denied", message: "" } },
		});
		open();
		await flush();
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		expect(document.getElementById("dp-state")?.textContent).toContain("doesn’t allow access");
		expect(document.querySelector("[data-dp-act='up']")).not.toBeNull();
	});

	it("given folders mode then file rows are not selectable", async () => {
		mockList({
			"": page("", [
				["Docs", true],
				["a.txt", false],
			]),
		});
		open(vi.fn(), "folders");
		await flush();
		const boxes = document.querySelectorAll<HTMLInputElement>("#dp-list input");
		expect(boxes[0]?.disabled).toBe(false);
		expect(boxes[1]?.disabled).toBe(true);
	});

	it("given a big folder then Show more fetches the next page", async () => {
		mockList({
			"": {
				...page(
					"",
					[
						["a", false],
						["b", false],
					],
					2,
				),
				total: 4,
			},
		});
		open();
		await flush();
		expect((document.getElementById("dp-more") as HTMLElement).hidden).toBe(false);
		expect(document.getElementById("dp-more-text")?.textContent).toContain("of 4");
	});
});
