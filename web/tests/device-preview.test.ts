import { describe, expect, it, vi } from "vitest";
import {
	buildPreviewUrl,
	createThumbLoader,
	FetchQueue,
	isImageName,
	isVideoName,
	outcomeForStatus,
	retriesOnVisible,
	stepIndex,
} from "../src/device-preview.ts";

const target = { method: "adb" as const, deviceId: "dev 1", path: "DCIM/Camera/a b&c.jpg", size: 123, mtime: 456 };
const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

describe("preview helpers", () => {
	it("given names when classified then images, videos and others are told apart", () => {
		expect(isImageName("IMG_1.JPG")).toBe(true);
		expect(isImageName("a.heic")).toBe(true);
		expect(isImageName("raw.dng")).toBe(false);
		expect(isImageName(".jpg")).toBe(false);
		expect(isVideoName("clip.MP4")).toBe(true);
		expect(isVideoName("a.jpg")).toBe(false);
	});

	it("given a target when building the url then every value is encoded", () => {
		const url = new URL(buildPreviewUrl("preview", target), "http://x");
		expect(url.pathname).toBe("/api/device/preview");
		expect(url.searchParams.get("path")).toBe("DCIM/Camera/a b&c.jpg");
		expect(url.searchParams.get("device_id")).toBe("dev 1");
		expect(url.searchParams.get("size")).toBe("123");
		expect(url.searchParams.get("mtime")).toBe("456");
		expect(url.searchParams.get("method")).toBe("adb");
		expect(buildPreviewUrl("thumb", target)).toContain("/api/device/thumb?");
	});

	it("given statuses when mapped then busy, too large and failures are distinct", () => {
		expect(outcomeForStatus(200)).toBe("ok");
		expect(outcomeForStatus(409)).toBe("busy");
		expect(outcomeForStatus(413)).toBe("toolarge");
		expect(outcomeForStatus(503)).toBe("unplugged");
		expect(outcomeForStatus(404)).toBe("failed");
		expect(retriesOnVisible("busy")).toBe(true);
		expect(retriesOnVisible("unplugged")).toBe(true);
		expect(retriesOnVisible("toolarge")).toBe(false);
		expect(retriesOnVisible("failed")).toBe(false);
	});

	it("given an index when stepping then it stops at both ends", () => {
		expect(stepIndex(0, -1, 3)).toBeNull();
		expect(stepIndex(2, 1, 3)).toBeNull();
		expect(stepIndex(1, 1, 3)).toBe(2);
		expect(stepIndex(-1, 1, 3)).toBe(0);
	});
});

describe("FetchQueue", () => {
	it("given six jobs when enqueued then at most four run and finishing one starts the next", async () => {
		const queue = new FetchQueue(4);
		const releases: Array<() => void> = [];
		const started: number[] = [];
		for (let i = 0; i < 6; i += 1) {
			queue.enqueue(
				(): Promise<void> =>
					new Promise<void>((resolve) => {
						started.push(i);
						releases.push(resolve);
					}),
			);
		}
		expect(queue.inFlight).toBe(4);
		expect(queue.queued).toBe(2);
		releases[0]?.();
		await flush();
		expect(started).toEqual([0, 1, 2, 3, 4]);
		expect(queue.inFlight).toBe(4);
	});

	it("given a queued job when cancelled then it never starts, and a running job gets aborted", async () => {
		const queue = new FetchQueue(1);
		let signal: AbortSignal | null = null;
		const second = vi.fn(async (): Promise<void> => undefined);
		const first = queue.enqueue((s: AbortSignal): Promise<void> => {
			signal = s;
			return new Promise<void>(() => undefined);
		});
		const queued = queue.enqueue(second);
		queued.cancel();
		first.cancel();
		await flush();
		expect((signal as AbortSignal | null)?.aborted).toBe(true);
		expect(second).not.toHaveBeenCalled();
		expect(queue.queued).toBe(0);
	});
});

class FakeObserver {
	static instances: FakeObserver[] = [];
	readonly observed = new Set<Element>();
	constructor(
		private readonly callback: (entries: Array<{ target: Element; isIntersecting: boolean }>) => void,
		readonly options?: IntersectionObserverInit,
	) {
		FakeObserver.instances.push(this);
	}
	observe(el: Element): void {
		this.observed.add(el);
	}
	unobserve(el: Element): void {
		this.observed.delete(el);
	}
	disconnect(): void {
		this.observed.clear();
	}
	emit(el: Element, isIntersecting: boolean): void {
		this.callback([{ target: el, isIntersecting }]);
	}
}

function thumb(): HTMLButtonElement {
	const button = document.createElement("button");
	button.className = "dp-thumb is-loading";
	button.innerHTML = '<span class="dp-thumb-img"></span><span class="dp-thumb-glyph"></span>';
	document.body.appendChild(button);
	return button;
}

describe("thumb loader", () => {
	it("given a visible tile when loaded then an img with an object url replaces the shimmer, and reset revokes it", async () => {
		FakeObserver.instances = [];
		vi.stubGlobal("IntersectionObserver", FakeObserver);
		const create = vi.fn(() => "blob:t1");
		const revoke = vi.fn();
		vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }));
		globalThis.fetch = vi.fn(async () => new Response(new Blob(["x"]), { status: 200 })) as typeof fetch;
		const loader = createThumbLoader(null);
		const button = thumb();
		loader.register(button, target);
		expect(globalThis.fetch).not.toHaveBeenCalled();
		FakeObserver.instances[0]?.emit(button, true);
		await flush();
		expect(button.classList.contains("is-loading")).toBe(false);
		expect(button.querySelector("img.dp-thumb-img")?.getAttribute("src")).toBe("blob:t1");
		expect(loader.objectUrlFor(button)).toBe("blob:t1");
		loader.reset();
		expect(revoke).toHaveBeenCalledWith("blob:t1");
		vi.unstubAllGlobals();
	});

	it("given error statuses when requested then 409 is plain, 413/404 failed for good, 503 retried on next visibility", async () => {
		FakeObserver.instances = [];
		vi.stubGlobal("IntersectionObserver", FakeObserver);
		const statuses = [409, 413, 404, 503];
		const calls: string[] = [];
		globalThis.fetch = vi.fn(async (url: unknown) => {
			calls.push(String(url));
			return new Response("{}", { status: statuses.shift() ?? 200 });
		}) as typeof fetch;
		const loader = createThumbLoader(null);
		const buttons = [thumb(), thumb(), thumb(), thumb()];
		for (const b of buttons) {
			loader.register(b, target);
			FakeObserver.instances[0]?.emit(b, true);
		}
		await flush();
		expect(buttons.map((b) => b.className)).toEqual([
			"dp-thumb is-busy",
			"dp-thumb is-toolarge",
			"dp-thumb is-failed",
			"dp-thumb is-failed",
		]);
		const before = calls.length;
		for (const b of buttons) {
			FakeObserver.instances[0]?.emit(b, false);
			FakeObserver.instances[0]?.emit(b, true);
		}
		await flush();
		expect(calls.length - before).toBe(2);
		loader.reset();
		vi.unstubAllGlobals();
	});

	it("given a queued tile that scrolls away when it leaves then it is dropped and asked again on return", async () => {
		FakeObserver.instances = [];
		vi.stubGlobal("IntersectionObserver", FakeObserver);
		const aborted: boolean[] = [];
		globalThis.fetch = vi.fn((_url: unknown, init?: RequestInit) => {
			return new Promise<Response>((_resolve, reject) => {
				init?.signal?.addEventListener("abort", () => {
					aborted.push(true);
					reject(new DOMException("aborted", "AbortError"));
				});
			});
		}) as typeof fetch;
		const loader = createThumbLoader(null, new FetchQueue(1));
		const [a, b] = [thumb(), thumb()];
		for (const t of [a, b]) {
			loader.register(t, target);
			FakeObserver.instances[0]?.emit(t, true);
		}
		expect(globalThis.fetch).toHaveBeenCalledTimes(1);
		FakeObserver.instances[0]?.emit(b, false);
		FakeObserver.instances[0]?.emit(a, false);
		await flush();
		expect(aborted).toEqual([true]);
		FakeObserver.instances[0]?.emit(b, true);
		await flush();
		expect(globalThis.fetch).toHaveBeenCalledTimes(2);
		loader.reset();
		vi.unstubAllGlobals();
	});
});
