import { beforeEach, describe, expect, it, vi } from "vitest";
import { deviceKind, initPickChooser } from "../src/pick-chooser.ts";

const HINTS = { ios: "ios hint", android: "android hint", other: "other hint" };
const ANDROID = "Mozilla/5.0 (Linux; Android 15; Pixel) Chrome/130";
const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari";
const DESKTOP = "Mozilla/5.0 (X11; Linux x86_64) Firefox/130";

function setup(userAgent: string) {
	document.body.innerHTML = `
		<button id="btn-pick-files" aria-expanded="false">x</button>
		<ul id="pick-menu" hidden>
			<li><button id="btn-pick-files-item">Files</button></li>
			<li><button id="btn-pick-folder">Folder</button></li>
		</ul>
		<input type="file" id="file-input" />
		<input type="file" id="folder-input" />
		<p id="device-hint"></p>`;
	const fileClick = vi.fn();
	const folderClick = vi.fn();
	(document.getElementById("file-input") as HTMLInputElement).click = fileClick;
	(document.getElementById("folder-input") as HTMLInputElement).click = folderClick;
	initPickChooser(document, userAgent, HINTS);
	return {
		button: document.getElementById("btn-pick-files") as HTMLButtonElement,
		menu: document.getElementById("pick-menu") as HTMLElement,
		hint: document.getElementById("device-hint") as HTMLElement,
		filesItem: document.getElementById("btn-pick-files-item") as HTMLButtonElement,
		folderItem: document.getElementById("btn-pick-folder") as HTMLButtonElement,
		fileClick,
		folderClick,
	};
}

describe("device kind", () => {
	it("given user agents when classified then iOS, Android and other are told apart", () => {
		// given / when / then
		expect(deviceKind(IPHONE)).toBe("ios");
		expect(deviceKind(ANDROID)).toBe("android");
		expect(deviceKind(DESKTOP)).toBe("other");
	});
});

describe("pick chooser", () => {
	beforeEach(() => {
		document.body.innerHTML = "";
	});

	it("given Android when initialised then one combined button and the Android hint show", () => {
		// given / when
		const { button, hint, menu } = setup(ANDROID);
		// then
		expect(button.textContent).toBe("Choose files or folder");
		expect(hint.textContent).toBe("android hint");
		expect(menu.hidden).toBe(true);
	});

	it("given Android when the button is clicked then the chooser opens without opening a picker", () => {
		// given
		const { button, menu, fileClick, folderClick } = setup(ANDROID);
		// when
		button.click();
		// then
		expect(menu.hidden).toBe(false);
		expect(button.getAttribute("aria-expanded")).toBe("true");
		expect(fileClick).not.toHaveBeenCalled();
		expect(folderClick).not.toHaveBeenCalled();
	});

	it("given the open chooser when Files is picked then the files input opens and the menu closes", () => {
		// given
		const { button, menu, filesItem, fileClick, folderClick } = setup(ANDROID);
		button.click();
		// when
		filesItem.click();
		// then
		expect(fileClick).toHaveBeenCalledOnce();
		expect(folderClick).not.toHaveBeenCalled();
		expect(menu.hidden).toBe(true);
	});

	it("given the open chooser when Folder is picked then the folder input opens", () => {
		// given
		const { button, folderItem, fileClick, folderClick } = setup(DESKTOP);
		button.click();
		// when
		folderItem.click();
		// then
		expect(folderClick).toHaveBeenCalledOnce();
		expect(fileClick).not.toHaveBeenCalled();
	});

	it("given iPhone when the button is clicked then it opens the files input directly with no chooser", () => {
		// given
		const { button, menu, hint, fileClick } = setup(IPHONE);
		// when
		button.click();
		// then
		expect(button.textContent).toBe("Choose");
		expect(hint.textContent).toBe("ios hint");
		expect(fileClick).toHaveBeenCalledOnce();
		expect(menu.hidden).toBe(true);
	});

	it("given the open chooser when Escape or an outside click happens then it closes", () => {
		// given
		const { button, menu } = setup(ANDROID);
		button.click();
		// when
		document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		// then
		expect(menu.hidden).toBe(true);
		button.click();
		document.body.click();
		expect(menu.hidden).toBe(true);
	});

	it("given missing elements when initialised then it does nothing and does not throw", () => {
		// given
		document.body.innerHTML = "";
		// when / then
		expect(() => initPickChooser(document, ANDROID, HINTS)).not.toThrow();
	});
});
