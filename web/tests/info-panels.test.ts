import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { bindInfoPanels } from "../src/info-panels.ts";

const HTML = `
<div>
	<button type="button" class="info-btn" id="btn-a" aria-expanded="false" aria-controls="panel-a">i</button>
	<div class="info-panel" id="panel-a" aria-hidden="true"></div>
	<button type="button" class="info-btn" id="btn-b" aria-expanded="false" aria-controls="panel-b">i</button>
	<div class="info-panel" id="panel-b" aria-hidden="true"></div>
	<button type="button" class="info-btn" id="btn-orphan" aria-expanded="false" aria-controls="missing">i</button>
</div>`;

const byId = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

beforeEach(() => {
	document.body.innerHTML = HTML;
	bindInfoPanels(document);
});

afterEach(() => {
	document.body.innerHTML = "";
});

describe("info panels", () => {
	it("given a closed panel when its info button is clicked then the panel shows and both aria attributes follow", () => {
		byId("btn-a").click();
		expect(byId("panel-a").classList.contains("visible")).toBe(true);
		expect(byId("panel-a").getAttribute("aria-hidden")).toBe("false");
		expect(byId("btn-a").getAttribute("aria-expanded")).toBe("true");
	});

	it("given an open panel when its info button is clicked again then it hides and the attributes reverse", () => {
		byId("btn-a").click();
		byId("btn-a").click();
		expect(byId("panel-a").classList.contains("visible")).toBe(false);
		expect(byId("panel-a").getAttribute("aria-hidden")).toBe("true");
		expect(byId("btn-a").getAttribute("aria-expanded")).toBe("false");
	});

	it("given two info buttons when one is clicked then the other panel is untouched", () => {
		byId("btn-a").click();
		expect(byId("panel-b").classList.contains("visible")).toBe(false);
	});

	it("given an info button whose panel is missing when clicked then nothing throws", () => {
		expect(() => byId("btn-orphan").click()).not.toThrow();
	});

	it("given an open panel when Escape is pressed then it closes and focus returns to its button", () => {
		byId("btn-a").click();
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
		expect(byId("panel-a").classList.contains("visible")).toBe(false);
		expect(byId("btn-a").getAttribute("aria-expanded")).toBe("false");
		expect(document.activeElement).toBe(byId("btn-a"));
	});

	it("given no open panel when Escape is pressed then focus is not moved", () => {
		byId("btn-b").focus();
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
		expect(document.activeElement).toBe(byId("btn-b"));
	});
});
