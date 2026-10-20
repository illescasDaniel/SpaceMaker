export type DeviceKind = "ios" | "android" | "other";

export interface PickChooserHints {
	ios: string;
	android: string;
	other: string;
}

export function deviceKind(userAgent: string): DeviceKind {
	if (/iPhone|iPad|iPod/i.test(userAgent)) {
		return "ios";
	}
	if (/Android/i.test(userAgent)) {
		return "android";
	}
	return "other";
}

function byId<T extends HTMLElement>(doc: Document, id: string): T | null {
	return doc.getElementById(id) as T | null;
}

/**
 * Phone upload pages: one button that opens a Files / Folder chooser (browser file inputs cannot
 * select both). iPhone keeps a single "Choose" button that opens the files input directly.
 */
export function initPickChooser(doc: Document, userAgent: string, hints: PickChooserHints): void {
	const button = byId<HTMLButtonElement>(doc, "btn-pick-files");
	const menu = byId<HTMLElement>(doc, "pick-menu");
	const filesItem = byId<HTMLButtonElement>(doc, "btn-pick-files-item");
	const folderItem = byId<HTMLButtonElement>(doc, "btn-pick-folder");
	const fileInput = byId<HTMLInputElement>(doc, "file-input");
	const folderInput = byId<HTMLInputElement>(doc, "folder-input");
	const hint = byId<HTMLElement>(doc, "device-hint");
	if (!button || !menu || !filesItem || !folderItem || !fileInput || !folderInput) {
		return;
	}
	const kind = deviceKind(userAgent);
	const single = kind === "ios";
	button.textContent = single ? "Choose" : "Choose files or folder";
	if (hint) {
		hint.textContent = hints[kind];
	}
	const setOpen = (open: boolean): void => {
		menu.hidden = !open;
		button.setAttribute("aria-expanded", String(open));
	};
	button.addEventListener("click", (ev) => {
		ev.stopPropagation();
		if (single) {
			fileInput.click();
			return;
		}
		setOpen(Boolean(menu.hidden));
	});
	filesItem.addEventListener("click", () => {
		setOpen(false);
		fileInput.click();
	});
	folderItem.addEventListener("click", () => {
		setOpen(false);
		folderInput.click();
	});
	doc.addEventListener("click", () => setOpen(false));
	doc.addEventListener("keydown", (ev) => {
		if (ev.key === "Escape") {
			setOpen(false);
		}
	});
}
