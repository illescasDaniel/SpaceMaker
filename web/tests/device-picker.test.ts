import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const showView = vi.fn();
vi.mock("../src/shell.ts", () => ({ showView: (...args: unknown[]) => showView(...args), applyState: vi.fn() }));

import { bindDevicePicker, formatSize, isMediaName, openDevicePicker, parentPath } from "../src/device-picker.ts";
import type { DeviceListPage } from "../src/types.ts";

const MARKUP = `
<span id="dp-bc-origin"></span><span id="dp-bc-title"></span><h2 id="dp-title"></h2>
<span id="dp-device-status-text"></span><div id="dp-device-status"></div><div id="dp-media-note" hidden></div>
<nav id="dp-trail"></nav><button id="btn-dp-up"></button><button id="btn-dp-select-folder"></button>
<input id="dp-filter" /><input type="checkbox" id="dp-hidden-toggle" />
<select id="dp-sort-select"><option value="name:asc">Name, A → Z</option><option value="name:desc">Name, Z → A</option><option value="mtime:desc">Newest first</option><option value="mtime:asc">Oldest first</option><option value="size:desc">Largest first</option><option value="size:asc">Smallest first</option></select>
<div id="dp-list-wrap"><div class="dp-head"><span></span>
<span><button type="button" class="dp-sort" data-dp-sort="name">Name <span class="dp-sort-arrow" aria-hidden="true"></span></button></span>
<span><button type="button" class="dp-sort" data-dp-sort="size">Size <span class="dp-sort-arrow" aria-hidden="true"></span></button></span>
<span class="dp-date"><button type="button" class="dp-sort" data-dp-sort="mtime">Modified <span class="dp-sort-arrow" aria-hidden="true"></span></button></span></div>
<p class="sr-only" id="dp-sort-status" aria-live="polite"></p><ul id="dp-list"></ul><div id="dp-state" hidden></div>
<div id="dp-more" hidden><span id="dp-more-text"></span><button id="btn-dp-more"></button></div></div>
<p id="dp-hint"></p><span id="dp-count"></span><button id="btn-dp-cancel"></button><button id="btn-dp-add"></button>
<div class="dp-lb" id="dp-lb" role="dialog" aria-modal="true" aria-labelledby="dp-lb-name" data-state="loading" hidden>
<div class="dp-lb-backdrop" data-dp-lb-close></div>
<div class="dp-lb-panel">
<div class="dp-lb-head">
<div class="dp-lb-meta">
<strong id="dp-lb-name"></strong>
<span class="dp-lb-info" id="dp-lb-info"></span>
</div>
<span class="dp-lb-pos" id="dp-lb-pos" aria-live="polite"></span>
<label class="dp-lb-sel"><input type="checkbox" id="dp-lb-sel" /> Selected</label>
<button type="button" class="dp-lb-btn" id="dp-lb-close" aria-label="Close preview">✕</button>
</div>
<div class="dp-lb-stage">
<button type="button" class="dp-lb-btn dp-lb-prev" id="dp-lb-prev" aria-label="Previous photo">←</button>
<div class="dp-lb-photo">
<div class="dp-lb-blur"></div>
<div class="dp-lb-full"></div>
<div class="dp-lb-glyph" aria-hidden="true">🎞</div>
<div class="dp-lb-note" role="status">Full preview unavailable for files over 25 MB</div>
<div class="dp-lb-loading" role="status"><span class="dp-spinner" aria-hidden="true"></span>Loading larger preview…</div>
<div class="dp-lb-error" role="alert"><strong>Preview unavailable</strong>You can still select this file.</div>
<div class="dp-lb-verror" role="alert"><strong>Video unavailable</strong>The phone was unplugged or didn’t respond. You can still select this file.</div>
</div>
<button type="button" class="dp-lb-btn dp-lb-next" id="dp-lb-next" aria-label="Next photo">→</button>
</div>
<p class="dp-lb-vnote">Playback isn’t available in the app yet. Transfer the video to watch it.</p>
<p class="dp-lb-hint">← → to browse · Esc to close</p>
</div>`;

interface ListBody {
	path: string;
	cursor: string | null;
	limit?: number;
	query?: string;
	show_hidden?: boolean;
	refresh?: boolean;
	sort?: string;
	order?: string;
}
type Reply = DeviceListPage | { status: number; detail: unknown };

function page(
	path: string,
	names: Array<[string, boolean]>,
	next: string | null = null,
	total?: number,
	echo?: { sort: string; order: string },
): DeviceListPage & { sort?: string; order?: string } {
	return {
		...echo,
		path,
		entries: names.map(([name, is_dir]) => ({ name, is_dir, size: 10, mtime: 0 })),
		next_cursor: next,
		total: total ?? names.length,
		total_unfiltered: total ?? names.length,
	};
}

/** Record every `/api/device/list` call; `handler` decides the reply (default: empty page for the path). */
function mockApi(handler: (body: ListBody) => Reply | Promise<Reply> = (body) => page(body.path, [])): ListBody[] {
	const calls: ListBody[] = [];
	globalThis.fetch = vi.fn(async (_url: unknown, init?: RequestInit) => {
		const body = JSON.parse(String(init?.body)) as ListBody;
		calls.push(body);
		const hit = await handler(body);
		if ("status" in hit) {
			return new Response(JSON.stringify({ detail: hit.detail }), { status: hit.status });
		}
		return new Response(JSON.stringify(hit), { status: 200 });
	}) as typeof fetch;
	return calls;
}

function mockList(pages: Record<string, Reply>): ListBody[] {
	return mockApi((body) => pages[body.path] ?? page(body.path, []));
}

const files = (prefix: string, count: number): Array<[string, boolean]> =>
	Array.from({ length: count }, (_, i) => [prefix + i, false] as [string, boolean]);

class FakeObserver {
	static instances: FakeObserver[] = [];
	readonly observed = new Set<Element>();
	disconnected = false;
	constructor(
		private readonly callback: (entries: Array<{ isIntersecting: boolean; target?: Element }>) => void,
		readonly options?: IntersectionObserverInit,
	) {
		FakeObserver.instances.push(this);
	}
	observe(target: Element): void {
		this.observed.add(target);
	}
	unobserve(target: Element): void {
		this.observed.delete(target);
	}
	disconnect(): void {
		this.observed.clear();
		this.disconnected = true;
	}
	fire(): void {
		this.callback([{ isIntersecting: true }]);
	}
	/** Report every observed element as visible (what the thumbnail loader needs to start fetching). */
	fireVisible(): void {
		this.callback([...this.observed].map((target) => ({ isIntersecting: true, target })));
	}
}
function fireIntersect(): void {
	FakeObserver.instances.at(-1)?.fire();
}

const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));
let bound = false;

beforeEach(() => {
	FakeObserver.instances = [];
	vi.stubGlobal("IntersectionObserver", FakeObserver);
	document.body.innerHTML = MARKUP;
	showView.mockClear();
	bound = false;
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
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

const labels = (): Array<string | null> =>
	[...document.querySelectorAll("#dp-list .dp-label")].map((n) => n.textContent);
const tick = (index: number): void => {
	const box = document.querySelectorAll<HTMLInputElement>("#dp-list input")[index] as HTMLInputElement;
	box.checked = true;
	box.dispatchEvent(new Event("change"));
};
const moreBtn = (): HTMLButtonElement => document.getElementById("btn-dp-more") as HTMLButtonElement;

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
		expect(labels()).toEqual(["<b>x</b>", "line\nbreak.txt"]);
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
		tick(1);
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		tick(0);
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

	it("given an empty folder then the empty state shows", async () => {
		mockList({ "": page("", []) });
		open();
		await flush();
		expect((document.getElementById("dp-state") as HTMLElement).hidden).toBe(false);
		expect(document.getElementById("dp-state")?.textContent).toContain("This folder is empty");
	});

	it("given the device unplugged then picks are kept and Retry lists again bypassing the cache", async () => {
		const calls = mockList({
			"": page("", [
				["a.txt", false],
				["Docs", true],
			]),
			Docs: { status: 409, detail: { error: "unplugged", message: "" } },
		});
		const onAdd = open();
		await flush();
		tick(0);
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		expect(document.querySelector("[data-dp-act='retry']")).not.toBeNull();
		expect(document.getElementById("dp-count")?.textContent).toContain("1");
		(document.querySelector("[data-dp-act='retry']") as HTMLButtonElement).click();
		await flush();
		expect(calls.at(-1)).toMatchObject({ path: "Docs", cursor: null, refresh: true });
		expect(onAdd).not.toHaveBeenCalled();
	});
});

describe("device picker pagination", () => {
	const bigFolder = (): ListBody[] =>
		mockApi((body) =>
			body.cursor === null
				? page("", files("a", 3), "c1", 7)
				: body.cursor === "c1"
					? page("", files("b", 3), "c2", 7)
					: page("", files("c", 1), null, 7),
		);

	it("given a folder when opened then page 1 is requested with limit 100 and no cursor", async () => {
		const calls = bigFolder();
		open();
		await flush();
		expect(calls).toHaveLength(1);
		expect(calls[0]).toMatchObject({ method: "adb", device_id: "dev1", path: "", cursor: null, limit: 100 });
		expect(calls[0]?.refresh).toBeFalsy();
	});

	it("given more pages then a sentinel is the last child and the observer is rooted on the list", async () => {
		bigFolder();
		open();
		await flush();
		const list = document.getElementById("dp-list") as HTMLElement;
		expect(list.lastElementChild?.classList.contains("dp-sentinel")).toBe(true);
		expect(list.lastElementChild?.getAttribute("aria-hidden")).toBe("true");
		const observer = FakeObserver.instances.at(-1);
		expect(observer?.options?.root).toBe(list);
		expect(observer?.observed.has(list.lastElementChild as Element)).toBe(true);
	});

	it("given the sentinel intersects twice while a page is in flight then exactly one request is made", async () => {
		let release: (reply: Reply) => void = () => undefined;
		const calls = mockApi((body) =>
			body.cursor === null
				? page("", files("a", 3), "c1", 6)
				: new Promise<Reply>((resolve) => {
						release = resolve;
					}),
		);
		open();
		await flush();
		fireIntersect();
		fireIntersect();
		await flush();
		expect(calls.filter((c) => c.cursor === "c1")).toHaveLength(1);
		expect(document.querySelector("#dp-list .dp-tail-row[role='status']")?.textContent).toContain("Loading more…");
		release(page("", files("b", 3), null, 6));
		await flush();
		expect(labels()).toHaveLength(6);
		expect(document.querySelector("#dp-list .dp-tail-row")).toBeNull();
	});

	it("given a next page when appended then existing rows keep their identity and the sentinel stays last", async () => {
		bigFolder();
		open();
		await flush();
		const before = [...document.querySelectorAll("#dp-list .dp-row")];
		fireIntersect();
		await flush();
		const after = [...document.querySelectorAll("#dp-list .dp-row")];
		expect(after).toHaveLength(6);
		before.forEach((li, i) => {
			expect(after[i]).toBe(li);
		});
		expect(document.getElementById("dp-list")?.lastElementChild?.classList.contains("dp-sentinel")).toBe(true);
		expect(FakeObserver.instances.at(-1)?.observed.size).toBe(1);
	});

	it("given the last page when loaded then the sentinel and the footer go away", async () => {
		bigFolder();
		open();
		await flush();
		fireIntersect();
		await flush();
		fireIntersect();
		await flush();
		expect(labels()).toHaveLength(7);
		expect(document.querySelector("#dp-list .dp-sentinel")).toBeNull();
		expect((document.getElementById("dp-more") as HTMLElement).hidden).toBe(true);
	});

	it("given more items than loaded then the footer shows the counts and Load more fetches the next page", async () => {
		const calls = bigFolder();
		open();
		await flush();
		expect((document.getElementById("dp-more") as HTMLElement).hidden).toBe(false);
		expect(document.getElementById("dp-more-text")?.textContent).toBe("Showing 3 of 7 items");
		moreBtn().click();
		await flush();
		expect(calls.at(-1)).toMatchObject({ path: "", cursor: "c1" });
		expect(document.getElementById("dp-more-text")?.textContent).toBe("Showing 6 of 7 items");
	});

	it("given a large total then the footer formats numbers with thousands separators", async () => {
		mockApi(() => page("", files("f", 100), "c1", 3412));
		open();
		await flush();
		expect(document.getElementById("dp-more-text")?.textContent).toBe("Showing 100 of 3,412 items");
	});

	it("given a page in flight then Load more is disabled", async () => {
		let release: (reply: Reply) => void = () => undefined;
		mockApi((body) =>
			body.cursor === null
				? page("", files("a", 3), "c1", 6)
				: new Promise<Reply>((resolve) => {
						release = resolve;
					}),
		);
		open();
		await flush();
		moreBtn().click();
		await flush();
		expect(moreBtn().disabled).toBe(true);
		release(page("", files("b", 3), null, 6));
		await flush();
		expect(moreBtn().disabled).toBe(false);
	});

	it("given no IntersectionObserver then the Load more button still pages", async () => {
		vi.stubGlobal("IntersectionObserver", undefined);
		const calls = bigFolder();
		open();
		await flush();
		moreBtn().click();
		await flush();
		expect(calls.at(-1)?.cursor).toBe("c1");
		expect(labels()).toHaveLength(6);
	});

	it("given a slow page for a folder we left then its response is dropped", async () => {
		let release: (reply: Reply) => void = () => undefined;
		mockApi((body) => {
			if (body.path === "" && body.cursor === null) {
				return page("", [["Docs", true], ...files("a", 2)], "c1", 6);
			}
			if (body.path === "" && body.cursor === "c1") {
				return new Promise<Reply>((resolve) => {
					release = resolve;
				});
			}
			return page("Docs", [["inner.txt", false]]);
		});
		open();
		await flush();
		fireIntersect();
		await flush();
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		release(page("", files("late", 3), null, 6));
		await flush();
		expect(labels()).toEqual(["inner.txt"]);
		expect(FakeObserver.instances.at(-1)?.observed.size ?? 0).toBe(0);
	});

	it("given the picker closes then the observer is disconnected", async () => {
		bigFolder();
		open();
		await flush();
		(document.getElementById("btn-dp-cancel") as HTMLButtonElement).click();
		expect(FakeObserver.instances.at(-1)?.disconnected).toBe(true);
	});

	it("given a next page fails then an inline Retry row keeps rows and ticks, and Retry resends the cursor with refresh", async () => {
		let failing = true;
		const calls = mockApi((body) => {
			if (body.cursor === null) {
				return page("", files("a", 3), "c1", 6);
			}
			if (failing) {
				return { status: 500, detail: { error: "failed", message: "" } };
			}
			return page("", files("b", 3), null, 6);
		});
		open();
		await flush();
		tick(1);
		fireIntersect();
		await flush();
		const tail = document.querySelector("#dp-list .dp-tail-row.is-error") as HTMLElement;
		expect(tail.textContent).toContain("Couldn’t load more items.");
		expect(labels()).toHaveLength(3);
		expect(document.getElementById("dp-count")?.textContent).toContain("1");
		expect((document.getElementById("dp-state") as HTMLElement).hidden).toBe(true);
		const requestsBefore = calls.length;
		expect(FakeObserver.instances.at(-1)?.observed.size).toBe(0);
		failing = false;
		(tail.querySelector("button") as HTMLButtonElement).click();
		await flush();
		expect(calls.length).toBe(requestsBefore + 1);
		expect(calls.at(-1)).toMatchObject({ cursor: "c1", refresh: true });
		expect(labels()).toHaveLength(6);
		expect(document.querySelector("#dp-list .dp-tail-row")).toBeNull();
		expect((document.querySelectorAll("#dp-list input")[1] as HTMLInputElement).checked).toBe(true);
	});

	it("given an invalid cursor then the listing restarts from page 1 keeping ticks", async () => {
		let stale = true;
		const calls = mockApi((body) => {
			if (body.cursor === null) {
				return page("", files("a", 3), "c1", 6);
			}
			if (stale) {
				stale = false;
				return { status: 400, detail: { error: "invalid_cursor", message: "" } };
			}
			return page("", files("b", 3), null, 6);
		});
		open();
		await flush();
		tick(2);
		fireIntersect();
		await flush();
		await flush();
		expect(calls.map((c) => c.cursor)).toEqual([null, "c1", null]);
		expect(labels()).toEqual(["a0", "a1", "a2"]);
		expect((document.querySelectorAll("#dp-list input")[2] as HTMLInputElement).checked).toBe(true);
		expect(document.getElementById("dp-count")?.textContent).toContain("1");
		expect(document.querySelector("#dp-list .dp-tail-row")).toBeNull();
	});
});

describe("device picker filter and hidden toggle", () => {
	it("given typing in the filter then one request carries the query after 200 ms and the list is dimmed meanwhile", async () => {
		vi.useFakeTimers();
		let release: (reply: Reply) => void = () => undefined;
		const calls = mockApi((body) =>
			body.query
				? new Promise<Reply>((resolve) => {
						release = resolve;
					})
				: page("", [...files("IMG_", 2), ["notes.txt", false]]),
		);
		open();
		await vi.advanceTimersByTimeAsync(0);
		const filter = document.getElementById("dp-filter") as HTMLInputElement;
		for (const text of ["i", "im", "img"]) {
			filter.value = text;
			filter.dispatchEvent(new Event("input"));
			await vi.advanceTimersByTimeAsync(50);
		}
		expect(calls).toHaveLength(1);
		await vi.advanceTimersByTimeAsync(200);
		expect(calls).toHaveLength(2);
		expect(calls[1]).toMatchObject({ path: "", cursor: null, query: "img" });
		const list = document.getElementById("dp-list") as HTMLElement;
		expect(list.classList.contains("is-refreshing")).toBe(true);
		expect(list.hidden).toBe(false);
		release(page("", files("IMG_", 2)));
		await vi.advanceTimersByTimeAsync(0);
		expect(list.classList.contains("is-refreshing")).toBe(false);
		expect(labels()).toHaveLength(2);
	});

	it("given a filter with no match then the No match state shows", async () => {
		vi.useFakeTimers();
		mockApi((body) => (body.query ? page("", []) : page("", [["a.txt", false]])));
		open();
		await vi.advanceTimersByTimeAsync(0);
		const filter = document.getElementById("dp-filter") as HTMLInputElement;
		filter.value = "zzz";
		filter.dispatchEvent(new Event("input"));
		await vi.advanceTimersByTimeAsync(200);
		expect(document.getElementById("dp-state")?.textContent).toContain("No match");
	});

	it("given the hidden toggle then show_hidden is sent immediately and ticks survive the restart", async () => {
		const calls = mockApi((body) =>
			body.show_hidden
				? page("", [
						[".thumbnails", true],
						["a.txt", false],
					])
				: page("", [["a.txt", false]]),
		);
		open();
		await flush();
		expect(calls[0]?.show_hidden).toBe(false);
		tick(0);
		const toggle = document.getElementById("dp-hidden-toggle") as HTMLInputElement;
		toggle.checked = true;
		toggle.dispatchEvent(new Event("change"));
		expect(calls).toHaveLength(2);
		expect(calls[1]).toMatchObject({ cursor: null, show_hidden: true });
		await flush();
		expect(labels()).toEqual([".thumbnails", "a.txt"]);
		expect((document.querySelectorAll("#dp-list input")[1] as HTMLInputElement).checked).toBe(true);
	});
});

describe("device picker sorting", () => {
	const arrow = (key: string): string | null =>
		document.querySelector(`[data-dp-sort="${key}"] .dp-sort-arrow`)?.textContent ?? null;
	const header = (key: string): HTMLButtonElement =>
		document.querySelector(`[data-dp-sort="${key}"]`) as HTMLButtonElement;
	const select = (): HTMLSelectElement => document.getElementById("dp-sort-select") as HTMLSelectElement;
	const echoFor = (body: ListBody): { sort: string; order: string } => ({
		sort: body.sort ?? "name",
		order: body.order ?? "asc",
	});

	it("given no stored sort when opened then no sort is sent and the echoed name/asc shows on the header and menu", async () => {
		const calls = mockApi((body) => page(body.path, [["a.txt", false]], null, 1, { sort: "name", order: "asc" }));
		open();
		await flush();
		expect(calls[0]?.sort).toBeUndefined();
		expect(calls[0]?.order).toBeUndefined();
		expect(arrow("name")).toBe("▲");
		expect(arrow("size")).toBe("");
		expect(arrow("mtime")).toBe("");
		expect(select().value).toBe("name:asc");
	});

	it("given a remembered size/desc then paging and folder opens carry it", async () => {
		const calls = mockApi((body) =>
			body.path === "" && body.cursor === null
				? page("", [["Docs", true], ...files("a", 2)], "c1", 6, { sort: "size", order: "desc" })
				: page(body.path, [["x.txt", false]], null, 6, echoFor(body)),
		);
		open();
		await flush();
		expect(arrow("size")).toBe("▼");
		expect(select().value).toBe("size:desc");
		fireIntersect();
		await flush();
		expect(calls.at(-1)).toMatchObject({ cursor: "c1", sort: "size", order: "desc" });
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		expect(calls.at(-1)).toMatchObject({ path: "Docs", sort: "size", order: "desc" });
	});

	it("given the Modified header then it sorts newest first, keeps filter, hidden and ticks, and flips on a second click", async () => {
		vi.useFakeTimers();
		const calls = mockApi((body) =>
			page(
				body.path,
				[
					["a.txt", false],
					["b.txt", false],
				],
				null,
				2,
				echoFor(body),
			),
		);
		open();
		await vi.advanceTimersByTimeAsync(0);
		const filter = document.getElementById("dp-filter") as HTMLInputElement;
		filter.value = "txt";
		filter.dispatchEvent(new Event("input"));
		await vi.advanceTimersByTimeAsync(200);
		const toggle = document.getElementById("dp-hidden-toggle") as HTMLInputElement;
		toggle.checked = true;
		toggle.dispatchEvent(new Event("change"));
		await vi.advanceTimersByTimeAsync(0);
		tick(1);
		const before = calls.length;
		header("mtime").click();
		expect(calls).toHaveLength(before + 1);
		expect(calls.at(-1)).toMatchObject({
			cursor: null,
			sort: "mtime",
			order: "desc",
			query: "txt",
			show_hidden: true,
		});
		await vi.advanceTimersByTimeAsync(0);
		expect(arrow("mtime")).toBe("▼");
		expect((document.querySelectorAll("#dp-list input")[1] as HTMLInputElement).checked).toBe(true);
		header("mtime").click();
		expect(calls.at(-1)).toMatchObject({ sort: "mtime", order: "asc" });
		await vi.advanceTimersByTimeAsync(0);
		expect(arrow("mtime")).toBe("▲");
	});

	it("given inactive Size and Name headers then their first click uses the natural direction", async () => {
		const calls = mockApi((body) => page(body.path, [["a.txt", false]], null, 1, echoFor(body)));
		open();
		await flush();
		header("size").click();
		await flush();
		expect(calls.at(-1)).toMatchObject({ sort: "size", order: "desc" });
		header("name").click();
		await flush();
		expect(calls.at(-1)).toMatchObject({ sort: "name", order: "asc" });
	});

	it("given a sort restart in flight then the list is dimmed but stays visible", async () => {
		let release: (reply: Reply) => void = () => undefined;
		mockApi((body) =>
			body.sort
				? new Promise<Reply>((resolve) => {
						release = resolve;
					})
				: page("", [["a.txt", false]], null, 1, { sort: "name", order: "asc" }),
		);
		open();
		await flush();
		header("size").click();
		await flush();
		const list = document.getElementById("dp-list") as HTMLElement;
		expect(list.classList.contains("is-refreshing")).toBe(true);
		expect(list.hidden).toBe(false);
		expect(labels()).toEqual(["a.txt"]);
		release(page("", [["b.txt", false]], null, 1, { sort: "size", order: "desc" }));
		await flush();
		expect(list.classList.contains("is-refreshing")).toBe(false);
		expect(labels()).toEqual(["b.txt"]);
	});

	it("given the Sort menu changed to mtime:desc then it behaves like the Modified header", async () => {
		const calls = mockApi((body) => page(body.path, [["a.txt", false]], null, 1, echoFor(body)));
		open();
		await flush();
		const before = calls.length;
		select().value = "mtime:desc";
		select().dispatchEvent(new Event("change"));
		expect(calls).toHaveLength(before + 1);
		expect(calls.at(-1)).toMatchObject({ cursor: null, sort: "mtime", order: "desc" });
		await flush();
		expect(arrow("mtime")).toBe("▼");
	});

	it("given a pending filter debounce when a sort header is clicked then one request carries both and no more follow", async () => {
		vi.useFakeTimers();
		const calls = mockApi((body) => page(body.path, [["a.txt", false]], null, 1, echoFor(body)));
		open();
		await vi.advanceTimersByTimeAsync(0);
		const before = calls.length;
		const filter = document.getElementById("dp-filter") as HTMLInputElement;
		filter.value = "img";
		filter.dispatchEvent(new Event("input"));
		await vi.advanceTimersByTimeAsync(50);
		header("mtime").click();
		expect(calls).toHaveLength(before + 1);
		expect(calls.at(-1)).toMatchObject({ query: "img", sort: "mtime", order: "desc" });
		await vi.advanceTimersByTimeAsync(1000);
		expect(calls).toHaveLength(before + 1);
	});

	it("given a sort then opening another folder keeps the sort but clears the filter", async () => {
		vi.useFakeTimers();
		const calls = mockApi((body) =>
			body.path === ""
				? page("", [["Docs", true]], null, 1, echoFor(body))
				: page(body.path, [["x.txt", false]], null, 1, echoFor(body)),
		);
		open();
		await vi.advanceTimersByTimeAsync(0);
		header("size").click();
		await vi.advanceTimersByTimeAsync(0);
		const filter = document.getElementById("dp-filter") as HTMLInputElement;
		filter.value = "Do";
		filter.dispatchEvent(new Event("input"));
		await vi.advanceTimersByTimeAsync(200);
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await vi.advanceTimersByTimeAsync(0);
		expect(calls.at(-1)).toMatchObject({ path: "Docs", sort: "size", order: "desc" });
		expect(calls.at(-1)?.query ?? "").toBe("");
		expect(filter.value).toBe("");
	});

	it("given a late response from before a sort change then it is dropped", async () => {
		const releases: Array<(reply: Reply) => void> = [];
		mockApi((body) =>
			body.sort
				? new Promise<Reply>((resolve) => {
						releases.push(resolve);
					})
				: page("", [["a.txt", false]], null, 1, { sort: "name", order: "asc" }),
		);
		open();
		await flush();
		header("size").click();
		header("mtime").click();
		await flush();
		expect(releases).toHaveLength(2);
		releases[1]?.(page("", [["new.txt", false]], null, 1, { sort: "mtime", order: "desc" }));
		await flush();
		releases[0]?.(page("", [["old.txt", false]], null, 1, { sort: "size", order: "desc" }));
		await flush();
		expect(labels()).toEqual(["new.txt"]);
	});

	it("given sort changes then header labels and the live region describe the order", async () => {
		mockApi((body) => page(body.path, [["a.txt", false]], null, 1, echoFor(body)));
		open();
		await flush();
		expect(header("size").getAttribute("aria-label")).toBe("Size. Sort largest first.");
		header("mtime").click();
		await flush();
		expect(header("mtime").getAttribute("aria-label")).toBe("Modified, sorted newest first. Sort oldest first.");
		expect(document.getElementById("dp-sort-status")?.textContent).toBe("Sorted newest first. Folders stay first.");
	});

	it("given a file with unknown mtime then its Modified cell shows a dash", async () => {
		mockApi((body) => page(body.path, [["a.txt", false]]));
		open();
		await flush();
		expect(document.querySelector("#dp-list .dp-date")?.textContent).toBe("—");
	});
});

describe("device picker photo rows", () => {
	it("given mixed files when listed then images and videos get a thumb and preview button, others 📄, and openers do not tick", async () => {
		mockList({
			"": page("", [
				["Camera", true],
				["a.jpg", false],
				["clip.mp4", false],
				["doc.pdf", false],
			]),
		});
		open();
		await flush();
		const rows = [...document.querySelectorAll<HTMLElement>("#dp-list .dp-row")];
		expect(rows[0]?.querySelector(".dp-ico")?.textContent).toBe("📁");
		expect(rows[1]?.querySelector("button.dp-thumb.is-loading")?.getAttribute("aria-label")).toBe("Preview a.jpg");
		expect(rows[1]?.querySelector(".dp-preview-btn")?.getAttribute("aria-label")).toBe("Preview a.jpg");
		expect(rows[1]?.querySelector(".dp-ico")).toBeNull();
		const video = rows[2]?.querySelector("button.dp-thumb.dp-thumb-video.is-loading");
		expect(video?.getAttribute("aria-label")).toBe("Preview clip.mp4 (video)");
		expect(video?.querySelector(".dp-thumb-glyph")?.textContent).toBe("🎞");
		expect(video?.querySelector(".dp-thumb-play")?.textContent).toBe("▶");
		expect(video?.querySelector(".dp-thumb-dur")?.textContent).toBe("");
		expect(rows[2]?.querySelector(".dp-preview-btn")?.getAttribute("aria-label")).toBe("Preview clip.mp4 (video)");
		expect(rows[2]?.querySelector(".dp-ico")).toBeNull();
		expect(rows[3]?.querySelector(".dp-ico")?.textContent).toBe("📄");
		rows[1]?.querySelector<HTMLButtonElement>(".dp-preview-btn")?.click();
		expect(document.querySelectorAll<HTMLInputElement>("#dp-list input:checked")).toHaveLength(0);
		expect(document.getElementById("btn-dp-add")?.hasAttribute("disabled")).toBe(true);
	});
});

describe("device picker lightbox and thumbnail loading", () => {
	const imageNames = ["a.jpg", "b.jpg", "c.jpg"];
	let previewSignals: AbortSignal[];

	/** List calls answer normally; thumb/preview fetches hang until their AbortSignal fires. */
	function mockWithHangingPreviews(handler: (body: ListBody) => Reply = (body) => page(body.path, [])): void {
		previewSignals = [];
		mockApi(handler);
		const listFetch = globalThis.fetch;
		globalThis.fetch = vi.fn((url: unknown, init?: RequestInit) => {
			if (String(url).includes("/api/device/") && !String(url).endsWith("/api/device/list")) {
				const signal = init?.signal as AbortSignal;
				previewSignals.push(signal);
				return new Promise<Response>((_resolve, reject) => {
					signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
				});
			}
			return listFetch(url as RequestInfo, init);
		}) as typeof fetch;
	}

	const lightbox = (): HTMLElement => document.getElementById("dp-lb") as HTMLElement;
	const thumbs = (): HTMLButtonElement[] => [...document.querySelectorAll<HTMLButtonElement>("#dp-list .dp-thumb")];
	const lbSel = (): HTMLInputElement => document.getElementById("dp-lb-sel") as HTMLInputElement;
	const mediaPage = (): DeviceListPage =>
		page(
			"",
			imageNames.map((name) => [name, false]),
		);

	async function openWithImages(): Promise<void> {
		mockWithHangingPreviews((body) => (body.path === "" ? mediaPage() : page(body.path, [["x.jpg", false]])));
		open();
		await flush();
	}

	it("given a row thumbnail when clicked then the lightbox opens on that image", async () => {
		await openWithImages();
		expect(lightbox().hidden).toBe(true);
		thumbs()[1]?.click();
		expect(lightbox().hidden).toBe(false);
		expect(document.getElementById("dp-lb-name")?.textContent).toBe("b.jpg");
	});

	it("given a row eye button when clicked then the lightbox opens on that image", async () => {
		await openWithImages();
		document.querySelectorAll<HTMLButtonElement>("#dp-list .dp-preview-btn")[2]?.click();
		expect(lightbox().hidden).toBe(false);
		expect(document.getElementById("dp-lb-name")?.textContent).toBe("c.jpg");
	});

	it("given Selected ticked in the lightbox then the row checkbox and the footer count follow", async () => {
		await openWithImages();
		const before = document.getElementById("dp-count")?.textContent;
		thumbs()[1]?.click();
		lbSel().checked = true;
		lbSel().dispatchEvent(new Event("change"));
		const boxes = document.querySelectorAll<HTMLInputElement>("#dp-list input");
		expect([...boxes].map((box) => box.checked)).toEqual([false, true, false]);
		expect(document.getElementById("dp-count")?.textContent).not.toBe(before);
		expect(document.getElementById("dp-count")?.textContent).toContain("1");
		expect(document.getElementById("btn-dp-add")?.hasAttribute("disabled")).toBe(false);
	});

	it("given the lightbox open when Tab and Shift+Tab are pressed at the ends then focus stays inside the dialog", async () => {
		await openWithImages();
		thumbs()[1]?.click();
		const focusable = [...lightbox().querySelectorAll<HTMLElement>("button:not([disabled]), input")];
		const first = focusable[0] as HTMLElement;
		const last = focusable.at(-1) as HTMLElement;
		last.focus();
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
		expect(document.activeElement).toBe(first);
		document.dispatchEvent(
			new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true }),
		);
		expect(document.activeElement).toBe(last);
		(document.getElementById("btn-dp-add") as HTMLElement).focus();
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
		expect(lightbox().contains(document.activeElement)).toBe(true);
	});

	function startThumbFetches(): void {
		FakeObserver.instances.find((observer) => observer.observed.has(thumbs()[0] as Element))?.fireVisible();
	}

	it("given in-flight thumbnail fetches when a folder is opened then they are aborted", async () => {
		mockWithHangingPreviews((body) =>
			body.path === ""
				? page("", [["Camera", true], ...imageNames.map((n) => [n, false] as [string, boolean])])
				: page(body.path, []),
		);
		open();
		await flush();
		startThumbFetches();
		await flush();
		expect(previewSignals.length).toBeGreaterThan(0);
		expect(previewSignals.every((signal) => !signal.aborted)).toBe(true);
		(document.querySelector("#dp-list button.dp-name") as HTMLButtonElement).click();
		await flush();
		expect(previewSignals.every((signal) => signal.aborted)).toBe(true);
	});

	it("given in-flight thumbnail fetches when the filter restarts the listing then they are aborted", async () => {
		await openWithImages();
		startThumbFetches();
		await flush();
		expect(previewSignals.length).toBeGreaterThan(0);
		const filter = document.getElementById("dp-hidden-toggle") as HTMLInputElement;
		filter.checked = true;
		filter.dispatchEvent(new Event("change"));
		await flush();
		expect(previewSignals.every((signal) => signal.aborted)).toBe(true);
	});
});

describe("device picker video rows", () => {
	const entries: Array<[string, boolean]> = [
		["a.jpg", false],
		["CLIP.MP4", false],
		["old.avi", false],
		["doc.pdf", false],
		["Camera", true],
		["z.png", false],
	];
	const thumbs = (): HTMLButtonElement[] => [...document.querySelectorAll<HTMLButtonElement>("#dp-list .dp-thumb")];
	const lbName = (): string => document.getElementById("dp-lb-name")?.textContent ?? "";
	const key = (k: string): void => {
		document.dispatchEvent(new KeyboardEvent("keydown", { key: k }));
	};

	function mockVideoApi(thumbReply: () => Response): void {
		mockApi((body) => page(body.path, body.path === "" ? entries : []));
		const listFetch = globalThis.fetch;
		globalThis.fetch = vi.fn(async (url: unknown, init?: RequestInit) => {
			if (String(url).includes("/api/device/thumb")) {
				return thumbReply();
			}
			if (String(url).includes("/api/device/preview")) {
				return new Response("{}", { status: 500 });
			}
			return listFetch(url as RequestInfo, init);
		}) as typeof fetch;
	}

	it("given a loaded poster when the duration is unknown then the preview button still says video", async () => {
		mockVideoApi(() => new Response(new Blob(["x"]), { status: 200 }));
		open();
		await flush();
		FakeObserver.instances.find((o) => o.observed.has(thumbs()[0] as Element))?.fireVisible();
		await flush();
		const video = thumbs()[1] as HTMLButtonElement;
		const eye = video.closest(".dp-row")?.querySelector(".dp-preview-btn");
		expect(video.getAttribute("aria-label")).toBe("Preview CLIP.MP4 (video)");
		expect(eye?.getAttribute("aria-label")).toBe("Preview CLIP.MP4 (video)");
	});

	it("given photos, videos and others when listed then only previewable videos get a thumb, others keep icons", async () => {
		mockVideoApi(() => new Response("{}", { status: 404 }));
		open();
		await flush();
		expect(thumbs()).toHaveLength(3);
		expect(thumbs().map((t) => t.classList.contains("dp-thumb-video"))).toEqual([false, true, false]);
		const avi = [...document.querySelectorAll("#dp-list .dp-row")].find((r) => r.textContent?.includes("old.avi"));
		expect(avi?.querySelector(".dp-ico-media")?.textContent).toBe("🎞");
		expect(avi?.querySelector(".dp-thumb")).toBeNull();
	});

	it("given a loaded poster when the duration header is known then badge and both aria-labels carry it", async () => {
		mockVideoApi(() => new Response(new Blob(["x"]), { status: 200, headers: { "X-Media-Duration": "42.4" } }));
		open();
		await flush();
		FakeObserver.instances.find((o) => o.observed.has(thumbs()[0] as Element))?.fireVisible();
		await flush();
		const video = thumbs()[1] as HTMLButtonElement;
		expect(video.querySelector(".dp-thumb-dur")?.textContent).toBe("0:42");
		expect(video.getAttribute("aria-label")).toBe("Preview CLIP.MP4 (video, 0:42)");
		const eye = video.closest(".dp-row")?.querySelector(".dp-preview-btn");
		expect(eye?.getAttribute("aria-label")).toBe("Preview CLIP.MP4 (video, 0:42)");
	});

	it("given photos, a video, an avi, a pdf and a folder when stepping then it visits the three previewable items", async () => {
		mockVideoApi(() => new Response("{}", { status: 404 }));
		open();
		await flush();
		thumbs()[0]?.click();
		expect(document.getElementById("dp-lb-pos")?.textContent).toBe("1 / 3");
		key("ArrowRight");
		expect(lbName()).toBe("CLIP.MP4");
		expect(document.getElementById("dp-lb-pos")?.textContent).toBe("2 / 3");
		expect(document.getElementById("dp-lb")?.dataset.kind).toBe("video");
		key("ArrowRight");
		expect(lbName()).toBe("z.png");
		expect(document.getElementById("dp-lb-pos")?.textContent).toBe("3 / 3");
		expect((document.getElementById("dp-lb-next") as HTMLButtonElement).disabled).toBe(true);
	});

	it("given the 👁 button of a video with a known duration when clicked then the caption has it", async () => {
		mockVideoApi(() => new Response(new Blob(["x"]), { status: 200, headers: { "X-Media-Duration": "3735" } }));
		open();
		await flush();
		FakeObserver.instances.find((o) => o.observed.has(thumbs()[0] as Element))?.fireVisible();
		await flush();
		thumbs()[1]?.closest(".dp-row")?.querySelector<HTMLButtonElement>(".dp-preview-btn")?.click();
		expect(document.getElementById("dp-lb-info")?.textContent).toMatch(/^Video · 1:02:15 · /);
		await flush();
		expect(document.getElementById("dp-lb")?.dataset.state).toBe("verror");
	});
});
