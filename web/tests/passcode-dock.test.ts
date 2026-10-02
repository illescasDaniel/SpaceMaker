import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/gallery-timeline.ts", () => ({ loadServerInfo: vi.fn() }));

import { loadServerInfo } from "../src/gallery-timeline.ts";
import { bindPasscodeDock } from "../src/passcode.ts";
import { S } from "../src/state.ts";

const DOCK_HTML = `
<fieldset id="passcode-dock" data-state="open">
	<div id="passcode-info-panel" hidden></div>
	<button type="button" id="btn-passcode-info" aria-expanded="false"></button>
	<input type="password" id="passcode-input" placeholder="Choose a passcode">
	<button type="button" id="btn-passcode-set"></button>
	<p id="passcode-open-status"></p>
	<button type="button" id="btn-passcode-change"></button>
	<button type="button" id="btn-passcode-clear"></button>
</fieldset>`;

function respond(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const byId = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
const flush = async (): Promise<void> => {
	for (let i = 0; i < 5; i++) {
		await Promise.resolve();
	}
	await new Promise((resolve) => setTimeout(resolve, 0));
};

let fetchMock: ReturnType<typeof vi.fn>;

async function mountDock(initial = { enabled: false, corrupt_warning: false }): Promise<void> {
	document.body.innerHTML = DOCK_HTML;
	fetchMock.mockResolvedValueOnce(respond(200, initial));
	bindPasscodeDock();
	await flush();
}

beforeEach(() => {
	fetchMock = vi.fn();
	vi.stubGlobal("fetch", fetchMock);
	S.lastQrSrcByElementId = { "easy-upload-qr": "/qr?x" };
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.mocked(loadServerInfo).mockClear();
});

describe("passcode dock", () => {
	it("given no passcode when loaded then the dock is open and says anyone can open the Gallery", async () => {
		await mountDock();
		expect(byId("passcode-dock").dataset.state).toBe("open");
		expect(byId("passcode-open-status").textContent).toContain("Not set");
	});

	it("given an active passcode when loaded then the dock shows the active state", async () => {
		await mountDock({ enabled: true, corrupt_warning: false });
		expect(byId("passcode-dock").dataset.state).toBe("active");
	});

	it("given a corrupt store when loaded then the warning is shown as an error", async () => {
		await mountDock({ enabled: false, corrupt_warning: true });
		expect(byId("passcode-open-status").textContent).toContain("could not be read");
		expect(byId("passcode-open-status").classList.contains("error")).toBe(true);
	});

	it("given a typed passcode when Set is clicked then it is PUT and the dock turns active", async () => {
		await mountDock();
		byId<HTMLInputElement>("passcode-input").value = "abcd";
		fetchMock.mockResolvedValueOnce(respond(200, { enabled: true, corrupt_warning: false }));
		byId("btn-passcode-set").click();
		await flush();
		const [url, init] = fetchMock.mock.calls[1] as [string, RequestInit];
		expect(url).toBe("/api/network-passcode");
		expect(init.method).toBe("PUT");
		expect(init.body).toBe(JSON.stringify({ passcode: "abcd" }));
		expect(byId("passcode-dock").dataset.state).toBe("active");
		expect(byId<HTMLInputElement>("passcode-input").value).toBe("");
	});

	it("given a passcode change when it succeeds then cached QR images are dropped and server info reloads", async () => {
		await mountDock();
		byId<HTMLInputElement>("passcode-input").value = "abcd";
		fetchMock.mockResolvedValueOnce(respond(200, { enabled: true, corrupt_warning: false }));
		byId("btn-passcode-set").click();
		await flush();
		expect(S.lastQrSrcByElementId).toEqual({});
		expect(loadServerInfo).toHaveBeenCalledTimes(1);
	});

	it("given a too-short passcode when Set is clicked then the server message is shown and the dock stays open", async () => {
		await mountDock();
		byId<HTMLInputElement>("passcode-input").value = "ab";
		fetchMock.mockResolvedValueOnce(respond(400, { detail: "Passcode must be at least 4 characters." }));
		byId("btn-passcode-set").click();
		await flush();
		expect(byId("passcode-open-status").textContent).toBe("Passcode must be at least 4 characters.");
		expect(byId("passcode-dock").dataset.state).toBe("open");
		expect(loadServerInfo).not.toHaveBeenCalled();
	});

	it("given Enter in the field when pressed then it submits like Set", async () => {
		await mountDock();
		byId<HTMLInputElement>("passcode-input").value = "abcd";
		fetchMock.mockResolvedValueOnce(respond(200, { enabled: true, corrupt_warning: false }));
		byId("passcode-input").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
		await flush();
		expect((fetchMock.mock.calls[1] as [string, RequestInit])[1].method).toBe("PUT");
	});

	it("given an active passcode when Clear is clicked then it is DELETEd and the dock opens", async () => {
		await mountDock({ enabled: true, corrupt_warning: false });
		fetchMock.mockResolvedValueOnce(respond(200, { enabled: false, corrupt_warning: false }));
		byId("btn-passcode-clear").click();
		await flush();
		expect((fetchMock.mock.calls[1] as [string, RequestInit])[1].method).toBe("DELETE");
		expect(byId("passcode-dock").dataset.state).toBe("open");
	});

	it("given an active passcode when Change is clicked then the field opens for a new passcode", async () => {
		await mountDock({ enabled: true, corrupt_warning: false });
		byId("btn-passcode-change").click();
		expect(byId("passcode-dock").dataset.state).toBe("open");
		expect(byId<HTMLInputElement>("passcode-input").placeholder).toBe("New passcode");
	});

	it("given Change is open when Escape is pressed then the dock returns to active", async () => {
		await mountDock({ enabled: true, corrupt_warning: false });
		byId("btn-passcode-change").click();
		fetchMock.mockResolvedValueOnce(respond(200, { enabled: true, corrupt_warning: false }));
		byId("passcode-input").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		await flush();
		expect(byId("passcode-dock").dataset.state).toBe("active");
	});

	it("given the info button when clicked then the panel toggles", async () => {
		await mountDock();
		byId("btn-passcode-info").click();
		expect(byId("passcode-info-panel").hasAttribute("hidden")).toBe(false);
		expect(byId("btn-passcode-info").getAttribute("aria-expanded")).toBe("true");
	});
});
