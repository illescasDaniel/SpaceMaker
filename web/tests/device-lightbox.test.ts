import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { LightboxItem } from "../src/device-lightbox.ts";
import { bindLightbox, closeLightbox, isLightboxOpen, openLightbox } from "../src/device-lightbox.ts";

const MARKUP = `
<div id="dp-lb" data-state="loading" hidden role="dialog">
<div data-dp-lb-close></div>
<strong id="dp-lb-name"></strong><span id="dp-lb-info"></span><span id="dp-lb-pos"></span>
<input type="checkbox" id="dp-lb-sel" /><button id="dp-lb-close"></button>
<button id="dp-lb-prev"></button><div class="dp-lb-blur"></div><div class="dp-lb-full"></div>
<div class="dp-lb-glyph">🎞</div><div class="dp-lb-verror"><strong>Video unavailable</strong></div><button id="dp-lb-next"></button>
<p class="dp-lb-vnote">Playback isn’t available in the app yet. Transfer the video to watch it.</p>
<p class="dp-lb-hint">← → to browse · Esc to close</p></div>
<button id="opener"></button>`;

const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));
const lb = (): HTMLElement => document.getElementById("dp-lb") as HTMLElement;
const text = (id: string): string => document.getElementById(id)?.textContent ?? "";

function items(selected: Set<string>, thumb: string | null = "blob:thumb"): LightboxItem[] {
	return ["a.jpg", "b.jpg", "c.jpg"].map((name) => ({
		path: "DCIM/" + name,
		name,
		info: "1 KB · 2026-01-01",
		target: { method: "adb" as const, deviceId: "d", path: "DCIM/" + name, size: 1, mtime: 2 },
		thumbUrl: () => thumb,
		isSelected: () => selected.has("DCIM/" + name),
		setSelected: (on: boolean) => {
			if (on) {
				selected.add("DCIM/" + name);
			} else {
				selected.delete("DCIM/" + name);
			}
		},
	}));
}

let urls: string[];
beforeEach(() => {
	document.body.innerHTML = MARKUP;
	urls = [];
	vi.stubGlobal(
		"URL",
		Object.assign(URL, { createObjectURL: () => "blob:full", revokeObjectURL: (u: string) => urls.push(u) }),
	);
});
afterEach(() => {
	closeLightbox();
	vi.unstubAllGlobals();
});

describe("device lightbox", () => {
	it("given three images when opened on the middle one then position, nav and blur thumbnail show", () => {
		globalThis.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
		bindLightbox({ items: () => items(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/b.jpg", document.getElementById("opener"));
		expect(isLightboxOpen()).toBe(true);
		expect(text("dp-lb-name")).toBe("b.jpg");
		expect(text("dp-lb-pos")).toBe("2 / 3");
		expect((document.getElementById("dp-lb-prev") as HTMLButtonElement).disabled).toBe(false);
		expect(lb().dataset.state).toBe("loading");
		expect(lb().querySelector(".dp-lb-blur img")?.getAttribute("src")).toBe("blob:thumb");
	});

	it("given arrow keys when stepping then it stops at the ends, aborts the previous fetch and Esc returns focus", () => {
		const signals: AbortSignal[] = [];
		globalThis.fetch = vi.fn((_u: unknown, init?: RequestInit) => {
			signals.push(init?.signal as AbortSignal);
			return new Promise<Response>(() => undefined);
		}) as typeof fetch;
		bindLightbox({ items: () => items(new Set()), selectionDisabled: () => false });
		const opener = document.getElementById("opener") as HTMLElement;
		openLightbox("DCIM/a.jpg", opener);
		expect((document.getElementById("dp-lb-prev") as HTMLButtonElement).disabled).toBe(true);
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
		expect(text("dp-lb-name")).toBe("a.jpg");
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		expect(text("dp-lb-name")).toBe("b.jpg");
		expect(signals[0]?.aborted).toBe(true);
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		expect(text("dp-lb-name")).toBe("c.jpg");
		expect((document.getElementById("dp-lb-next") as HTMLButtonElement).disabled).toBe(true);
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		expect(isLightboxOpen()).toBe(false);
		expect(signals.every((s) => s.aborted)).toBe(true);
		expect(document.activeElement).toBe(opener);
	});

	it("given the Selected checkbox when toggled then the row selection follows, and folders mode disables it", () => {
		globalThis.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
		const selected = new Set<string>(["DCIM/a.jpg"]);
		let folders = false;
		bindLightbox({ items: () => items(selected), selectionDisabled: () => folders });
		openLightbox("DCIM/a.jpg", null);
		const sel = document.getElementById("dp-lb-sel") as HTMLInputElement;
		expect(sel.checked).toBe(true);
		sel.checked = false;
		sel.dispatchEvent(new Event("change"));
		expect(selected.size).toBe(0);
		closeLightbox();
		folders = true;
		openLightbox("DCIM/b.jpg", null);
		expect(sel.disabled).toBe(true);
	});

	it("given the preview replies when ok, 413 or 500 then the state is ok, toolarge or error", async () => {
		const replies = [
			new Response(new Blob(["x"]), { status: 200 }),
			new Response("{}", { status: 413 }),
			new Response("{}", { status: 500 }),
		];
		globalThis.fetch = vi.fn(async () => replies.shift() as Response) as typeof fetch;
		bindLightbox({ items: () => items(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/a.jpg", null);
		await flush();
		lb().querySelector(".dp-lb-full img")?.dispatchEvent(new Event("load"));
		expect(lb().dataset.state).toBe("ok");
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		await flush();
		expect(urls).toContain("blob:full");
		expect(lb().dataset.state).toBe("toolarge");
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		await flush();
		expect(lb().dataset.state).toBe("error");
	});

	it("given the error state when selecting, stepping with arrows and pressing Esc then all still work", async () => {
		const fetchMock = vi.fn(async () => new Response("{}", { status: 500 }));
		globalThis.fetch = fetchMock as unknown as typeof fetch;
		const selected = new Set<string>();
		bindLightbox({ items: () => items(selected), selectionDisabled: () => false });
		const opener = document.getElementById("opener") as HTMLElement;
		openLightbox("DCIM/b.jpg", opener);
		await flush();
		expect(lb().dataset.state).toBe("error");
		const sel = document.getElementById("dp-lb-sel") as HTMLInputElement;
		sel.checked = true;
		sel.dispatchEvent(new Event("change"));
		expect(selected.has("DCIM/b.jpg")).toBe(true);
		const requestsBefore = fetchMock.mock.calls.length;
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
		expect(text("dp-lb-name")).toBe("c.jpg");
		await flush();
		expect(fetchMock.mock.calls.length).toBe(requestsBefore + 1);
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
		expect(text("dp-lb-name")).toBe("b.jpg");
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		expect(isLightboxOpen()).toBe(false);
		expect(document.activeElement).toBe(opener);
	});

	it("given a 413 without a thumbnail when opened then the error state shows", async () => {
		globalThis.fetch = vi.fn(async () => new Response("{}", { status: 413 })) as typeof fetch;
		bindLightbox({ items: () => items(new Set(), null), selectionDisabled: () => false });
		openLightbox("DCIM/a.jpg", null);
		await flush();
		expect(lb().dataset.state).toBe("error");
	});
});

describe("device lightbox with videos", () => {
	function mixed(
		selected: Set<string>,
		duration: number | null = 42.4,
		kinds: Array<"image" | "video"> = ["image", "video", "image"],
	): LightboxItem[] {
		return items(selected).map((item, i) => ({
			...item,
			kind: kinds[i] ?? "image",
			info: kinds[i] === "video" ? "86.0 MB · 2026-01-01" : item.info,
			durationSeconds: () => duration,
		}));
	}
	const key = (k: string): void => {
		document.dispatchEvent(new KeyboardEvent("keydown", { key: k }));
	};

	it("given photos and videos when opened on the video then the counter counts both, kind is video and the large frame is requested", () => {
		const urlsFetched: string[] = [];
		globalThis.fetch = vi.fn((u: unknown) => {
			urlsFetched.push(String(u));
			return new Promise<Response>(() => undefined);
		}) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/b.jpg", null);
		expect(text("dp-lb-pos")).toBe("2 / 3");
		expect(lb().dataset.kind).toBe("video");
		expect(lb().dataset.state).toBe("loading");
		expect(lb().querySelector(".dp-lb-blur img")?.getAttribute("src")).toBe("blob:thumb");
		expect(urlsFetched[0]).toContain("/api/device/preview?");
		key("ArrowLeft");
		expect(lb().dataset.kind).toBe("image");
	});

	it("given a video when shown then the caption has duration, size and date, and the note and hint are present with no player", () => {
		globalThis.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/b.jpg", null);
		expect(text("dp-lb-info")).toBe("Video · 0:42 · 86.0 MB · 2026-01-01");
		expect(lb().querySelector(".dp-lb-vnote")?.textContent).toBe(
			"Playback isn’t available in the app yet. Transfer the video to watch it.",
		);
		expect(lb().querySelector(".dp-lb-hint")?.textContent).toBe("← → to browse · Esc to close");
		expect(lb().querySelector("video")).toBeNull();
		expect(lb().querySelector("[data-dp-lb-play], .dp-lb-play")).toBeNull();
	});

	it("given a video of unknown duration then the caption omits the duration", () => {
		globalThis.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set(), null), selectionDisabled: () => false });
		openLightbox("DCIM/b.jpg", null);
		expect(text("dp-lb-info")).toBe("Video · 86.0 MB · 2026-01-01");
	});

	it("given a photo then the caption is unchanged and kind is image", () => {
		globalThis.fetch = vi.fn(() => new Promise<Response>(() => undefined)) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/a.jpg", null);
		expect(text("dp-lb-info")).toBe("1 KB · 2026-01-01");
		expect(lb().dataset.kind).toBe("image");
	});

	it("given the large frame loads then the state is ok", async () => {
		globalThis.fetch = vi.fn(async () => new Response(new Blob(["x"]), { status: 200 })) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/b.jpg", null);
		await flush();
		lb().querySelector(".dp-lb-full img")?.dispatchEvent(new Event("load"));
		expect(lb().dataset.state).toBe("ok");
	});

	it("given the large frame fails then Video unavailable shows and Selected, arrows and Esc still work", async () => {
		globalThis.fetch = vi.fn(async () => new Response("{}", { status: 500 })) as typeof fetch;
		const selected = new Set<string>();
		bindLightbox({ items: () => mixed(selected), selectionDisabled: () => false });
		const opener = document.getElementById("opener") as HTMLElement;
		openLightbox("DCIM/b.jpg", opener);
		await flush();
		expect(lb().dataset.state).toBe("verror");
		expect(lb().querySelector(".dp-lb-verror")?.textContent).toContain("Video unavailable");
		const sel = document.getElementById("dp-lb-sel") as HTMLInputElement;
		sel.checked = true;
		sel.dispatchEvent(new Event("change"));
		expect(selected.has("DCIM/b.jpg")).toBe(true);
		key("ArrowRight");
		expect(text("dp-lb-name")).toBe("c.jpg");
		key("ArrowLeft");
		expect(text("dp-lb-name")).toBe("b.jpg");
		key("Escape");
		expect(isLightboxOpen()).toBe(false);
		expect(document.activeElement).toBe(opener);
	});

	it("given a failing photo then the state stays error, not verror", async () => {
		globalThis.fetch = vi.fn(async () => new Response("{}", { status: 500 })) as typeof fetch;
		bindLightbox({ items: () => mixed(new Set()), selectionDisabled: () => false });
		openLightbox("DCIM/a.jpg", null);
		await flush();
		expect(lb().dataset.state).toBe("error");
	});
});
