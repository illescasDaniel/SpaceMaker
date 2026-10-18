import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bindUrlFields, setUrlField } from "../src/url-field.ts";

const LONG = `http://192.168.1.100:8765/gallery#k=${"ab".repeat(32)}`;

const HTML = `
<div class="url-field" id="uf">
	<input type="text" readonly id="uf-input" aria-label="Gallery URL" value="">
	<button type="button" class="url-copy" id="uf-copy" aria-label="Copy URL" disabled></button>
	<span class="sr-only" role="status" aria-live="polite" data-copy-status id="uf-status"></span>
</div>`;

const byId = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
const flush = async (): Promise<void> => {
	for (let i = 0; i < 5; i++) {
		await Promise.resolve();
	}
};

function stubClipboard(writeText: ((text: string) => Promise<void>) | undefined, secure: boolean): void {
	Object.defineProperty(navigator, "clipboard", { value: writeText ? { writeText } : undefined, configurable: true });
	Object.defineProperty(window, "isSecureContext", { value: secure, configurable: true });
}

function stubExecCommand(result: boolean | "throw"): ReturnType<typeof vi.fn> {
	const exec = vi.fn(() => {
		if (result === "throw") {
			throw new Error("blocked");
		}
		return result;
	});
	Object.defineProperty(document, "execCommand", { value: exec, configurable: true });
	return exec;
}

beforeEach(() => {
	document.body.innerHTML = HTML;
	bindUrlFields(document);
	setUrlField("uf-input", LONG);
});

afterEach(() => {
	vi.useRealTimers();
	document.body.innerHTML = "";
});

describe("url field", () => {
	it("given a known url when set then the input holds it and Copy is enabled", () => {
		expect(byId<HTMLInputElement>("uf-input").value).toBe(LONG);
		expect(byId<HTMLButtonElement>("uf-copy").disabled).toBe(false);
	});

	it("given an empty url when set then the input is empty and Copy is disabled", () => {
		setUrlField("uf-input", "");
		expect(byId<HTMLInputElement>("uf-input").value).toBe("");
		expect(byId<HTMLButtonElement>("uf-copy").disabled).toBe(true);
	});

	it("given markup characters in the url when set then they stay plain text in the input", () => {
		setUrlField("uf-input", 'http://x/<b>"a"</b>');
		expect(byId<HTMLInputElement>("uf-input").value).toBe('http://x/<b>"a"</b>');
		expect(document.querySelector("#uf b")).toBeNull();
	});

	it("given execCommand works when Copy is clicked then the clipboard api is never touched and Copied shows then reverts", async () => {
		vi.useFakeTimers();
		const writeText = vi.fn().mockResolvedValue(undefined);
		stubClipboard(writeText, true);
		const exec = stubExecCommand(true);
		byId("uf-copy").click();
		await flush();
		expect(exec).toHaveBeenCalledWith("copy");
		expect(writeText).not.toHaveBeenCalled();
		expect(byId("uf-copy").classList.contains("copied")).toBe(true);
		vi.advanceTimersByTime(1600);
		expect(byId("uf-copy").classList.contains("copied")).toBe(false);
	});

	it("given a successful copy when it happens then the stable live region announces Copied and clears with the button", async () => {
		vi.useFakeTimers();
		stubClipboard(undefined, false);
		stubExecCommand(true);
		byId("uf-copy").click();
		await flush();
		expect(byId("uf-status").textContent).toBe("Copied");
		vi.advanceTimersByTime(1600);
		expect(byId("uf-status").textContent).toBe("");
	});

	it("given two quick copies when the first timer would fire then Copied stays until the second timer ends", async () => {
		vi.useFakeTimers();
		stubClipboard(undefined, false);
		stubExecCommand(true);
		byId("uf-copy").click();
		await flush();
		vi.advanceTimersByTime(1000);
		byId("uf-copy").click();
		await flush();
		vi.advanceTimersByTime(700);
		expect(byId("uf-copy").classList.contains("copied")).toBe(true);
		vi.advanceTimersByTime(900);
		expect(byId("uf-copy").classList.contains("copied")).toBe(false);
	});

	it("given execCommand fails in a secure context when Copy is clicked then the clipboard api gets exactly the url", async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		stubClipboard(writeText, true);
		stubExecCommand(false);
		byId("uf-copy").click();
		await flush();
		expect(writeText).toHaveBeenCalledWith(LONG);
		expect(byId("uf-copy").classList.contains("copied")).toBe(true);
	});

	it("given execCommand fails in a non-secure context when Copy is clicked then the clipboard api is not used and no Copied shows", async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		stubClipboard(writeText, false);
		stubExecCommand(false);
		byId("uf-copy").click();
		await flush();
		expect(writeText).not.toHaveBeenCalled();
		expect(byId("uf-copy").classList.contains("copied")).toBe(false);
	});

	it("given both copy methods fail when Copy is clicked then no Copied shows and the url stays selected", async () => {
		stubClipboard(undefined, false);
		stubExecCommand("throw");
		byId("uf-copy").click();
		await flush();
		const input = byId<HTMLInputElement>("uf-input");
		expect(byId("uf-copy").classList.contains("copied")).toBe(false);
		expect(input.selectionStart).toBe(0);
		expect(input.selectionEnd).toBe(LONG.length);
	});

	it("given the input when focused then the whole url is selected", () => {
		const input = byId<HTMLInputElement>("uf-input");
		input.dispatchEvent(new FocusEvent("focus"));
		expect(input.selectionStart).toBe(0);
		expect(input.selectionEnd).toBe(LONG.length);
	});

	it("given an unknown input id when set then nothing throws", () => {
		expect(() => setUrlField("nope", LONG)).not.toThrow();
	});
});
