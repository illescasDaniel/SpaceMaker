import { beforeEach, describe, expect, it } from "vitest";
import { bindAddMenus } from "../src/lan.ts";

function setup(): { button: HTMLElement; menu: HTMLElement; item: HTMLElement } {
	document.body.innerHTML = `
		<div class="add-menu-wrap">
			<button type="button" class="btn-add-more" aria-expanded="false">Add</button>
			<ul class="add-menu" hidden><li><button id="item">Files…</button></li></ul>
		</div>`;
	bindAddMenus();
	return {
		button: document.querySelector<HTMLElement>(".btn-add-more") as HTMLElement,
		menu: document.querySelector<HTMLElement>(".add-menu") as HTMLElement,
		item: document.getElementById("item") as HTMLElement,
	};
}

describe("add menu", () => {
	beforeEach(() => {
		document.body.innerHTML = "";
	});

	it("given a closed menu when the button is clicked then it opens and flags aria-expanded", () => {
		// given
		const { button, menu } = setup();
		// when
		button.click();
		// then
		expect(menu.hidden).toBe(false);
		expect(button.getAttribute("aria-expanded")).toBe("true");
	});

	it("given an open menu when an item is picked then it closes", () => {
		// given
		const { button, menu, item } = setup();
		button.click();
		// when
		item.click();
		// then
		expect(menu.hidden).toBe(true);
		expect(button.getAttribute("aria-expanded")).toBe("false");
	});

	it("given an open menu when Escape is pressed then it closes", () => {
		// given
		const { button, menu } = setup();
		button.click();
		// when
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		// then
		expect(menu.hidden).toBe(true);
	});

	it("given an open menu when clicking elsewhere then it closes", () => {
		// given
		const { button, menu } = setup();
		button.click();
		// when
		document.body.click();
		// then
		expect(menu.hidden).toBe(true);
	});
});
