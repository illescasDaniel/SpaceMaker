import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bindUnlock } from "../src/unlock.ts";

const PAGE = `
<form id="unlock-form">
	<input id="passcode" type="password">
	<p id="msg"></p>
	<button type="submit" id="btn-unlock"></button>
</form>`;

function respond(status: number, body: unknown = {}): Response {
	return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const flush = async (): Promise<void> => {
	for (let i = 0; i < 6; i++) {
		await Promise.resolve();
	}
};

const input = (): HTMLInputElement => document.getElementById("passcode") as HTMLInputElement;
const button = (): HTMLButtonElement => document.getElementById("btn-unlock") as HTMLButtonElement;
const msg = (): HTMLElement => document.getElementById("msg") as HTMLElement;

interface Env {
	fetchFn: ReturnType<typeof vi.fn>;
	reload: ReturnType<typeof vi.fn>;
	replaceState: ReturnType<typeof vi.fn>;
}

function mount(hash = ""): Env {
	document.body.innerHTML = PAGE;
	const fetchFn = vi.fn();
	const reload = vi.fn();
	const replaceState = vi.fn();
	const loc = { hash, pathname: "/gallery", search: "?a=1", reload } as unknown as Location;
	const hist = { replaceState } as unknown as History;
	bindUnlock({ doc: document, fetchFn: fetchFn as unknown as typeof fetch, loc, hist });
	return { fetchFn, reload, replaceState };
}

function submit(value: string): void {
	input().value = value;
	document.getElementById("unlock-form")?.dispatchEvent(new Event("submit", { cancelable: true }));
}

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe("unlock page", () => {
	it("given a QR token in the fragment when loaded then it is POSTed in the body, never in the URL", () => {
		document.body.innerHTML = PAGE;
		const fetchFn = vi.fn().mockResolvedValue(respond(200));
		const loc = { hash: "#k=abc123", pathname: "/", search: "", reload: vi.fn() } as unknown as Location;
		bindUnlock({
			doc: document,
			fetchFn: fetchFn as unknown as typeof fetch,
			loc,
			hist: { replaceState: vi.fn() } as unknown as History,
		});
		const [url, init] = fetchFn.mock.calls[0] as [string, RequestInit];
		expect(url).toBe("/api/unlock");
		expect(init.method).toBe("POST");
		expect(init.body).toBe(JSON.stringify({ token: "abc123" }));
	});

	it("given a successful unlock when it completes then the fragment is dropped and the page reloads", async () => {
		document.body.innerHTML = PAGE;
		const fetchFn = vi.fn().mockResolvedValue(respond(200));
		const reload = vi.fn();
		const replaceState = vi.fn();
		const loc = { hash: "#k=tok", pathname: "/gallery", search: "?a=1", reload } as unknown as Location;
		bindUnlock({
			doc: document,
			fetchFn: fetchFn as unknown as typeof fetch,
			loc,
			hist: { replaceState } as unknown as History,
		});
		await flush();
		expect(replaceState).toHaveBeenCalledWith(null, "", "/gallery?a=1");
		expect(reload).toHaveBeenCalledTimes(1);
	});

	it("given a typed passcode when submitted then it is POSTed in the body", async () => {
		const env = mount();
		env.fetchFn.mockResolvedValue(respond(200));
		submit("hunter22");
		await flush();
		const [, init] = env.fetchFn.mock.calls[0] as [string, RequestInit];
		expect(init.body).toBe(JSON.stringify({ passcode: "hunter22" }));
		expect(env.reload).toHaveBeenCalledTimes(1);
	});

	it("given an empty field when submitted then nothing is sent", async () => {
		const env = mount();
		submit("");
		await flush();
		expect(env.fetchFn).not.toHaveBeenCalled();
	});

	it("given a wrong passcode when submitted then an error is shown and the page stays", async () => {
		const env = mount();
		env.fetchFn.mockResolvedValue(respond(401, { detail: "wrong-passcode" }));
		submit("nope");
		await flush();
		expect(msg().textContent).toBe("Wrong passcode. Try again.");
		expect(msg().classList.contains("error")).toBe(true);
		expect(env.reload).not.toHaveBeenCalled();
		expect(button().disabled).toBe(false);
	});

	it("given a lockout when submitted then the form is disabled with a countdown and re-enabled after", async () => {
		const env = mount();
		env.fetchFn.mockResolvedValue(respond(429, { detail: "locked-out", retry_after_seconds: 3 }));
		submit("nope");
		await flush();
		expect(input().disabled).toBe(true);
		expect(button().disabled).toBe(true);
		expect(msg().textContent).toContain("3 seconds");
		vi.advanceTimersByTime(4000);
		expect(input().disabled).toBe(false);
		expect(button().disabled).toBe(false);
		expect(msg().textContent).toBe("");
	});

	it("given the network is down when submitted then a reachability message is shown", async () => {
		const env = mount();
		env.fetchFn.mockRejectedValue(new TypeError("offline"));
		submit("abcd");
		await flush();
		expect(msg().textContent).toBe("Could not reach SpaceMaker.");
	});
});
