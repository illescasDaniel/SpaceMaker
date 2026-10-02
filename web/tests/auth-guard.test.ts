import { afterEach, describe, expect, it, vi } from "vitest";
import { installAuthGuard } from "../src/auth-guard.ts";

function fakeWindow(response: Response): { win: Window & typeof globalThis; reload: ReturnType<typeof vi.fn> } {
	const reload = vi.fn();
	const win = {
		fetch: vi.fn().mockResolvedValue(response),
		location: { reload },
	} as unknown as Window & typeof globalThis;
	return { win, reload };
}

const json = (status: number, body: unknown): Response =>
	new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
	vi.restoreAllMocks();
});

describe("auth guard", () => {
	it("given a passcode-required 401 when fetch resolves then the page reloads and the response is still returned", async () => {
		const { win, reload } = fakeWindow(json(401, { detail: "passcode-required" }));
		installAuthGuard(win);
		const response = await win.fetch("/api/anything");
		expect(reload).toHaveBeenCalledTimes(1);
		expect(response.status).toBe(401);
	});

	it("given any other 401 when fetch resolves then the page does not reload", async () => {
		const { win, reload } = fakeWindow(json(401, { detail: "something-else" }));
		installAuthGuard(win);
		await win.fetch("/api/anything");
		expect(reload).not.toHaveBeenCalled();
	});

	it("given a non-JSON 401 when fetch resolves then the page does not reload", async () => {
		const { win, reload } = fakeWindow(new Response("nope", { status: 401 }));
		installAuthGuard(win);
		await win.fetch("/api/anything");
		expect(reload).not.toHaveBeenCalled();
	});

	it("given a successful response when fetch resolves then it passes through untouched", async () => {
		const { win, reload } = fakeWindow(json(200, { ok: true }));
		installAuthGuard(win);
		const response = await win.fetch("/api/anything");
		expect(await response.json()).toEqual({ ok: true });
		expect(reload).not.toHaveBeenCalled();
	});
});
