export function deviceKind(userAgent) {
	if (/iPhone|iPad|iPod/i.test(userAgent)) {
		return "ios";
	}
	if (/Android/i.test(userAgent)) {
		return "android";
	}
	return "other";
}
function byId(doc, id) {
	return doc.getElementById(id);
}
/**
 * Phone upload pages: one button that opens a Files / Folder chooser (browser file inputs cannot
 * select both). iPhone keeps a single "Choose" button that opens the files input directly.
 */
export function initPickChooser(doc, userAgent, hints) {
	const button = byId(doc, "btn-pick-files");
	const menu = byId(doc, "pick-menu");
	const filesItem = byId(doc, "btn-pick-files-item");
	const folderItem = byId(doc, "btn-pick-folder");
	const fileInput = byId(doc, "file-input");
	const folderInput = byId(doc, "folder-input");
	const hint = byId(doc, "device-hint");
	if (!button || !menu || !filesItem || !folderItem || !fileInput || !folderInput) {
		return;
	}
	const kind = deviceKind(userAgent);
	const single = kind === "ios";
	button.textContent = single ? "Choose" : "Choose files or folder";
	if (hint) {
		hint.textContent = hints[kind];
	}
	const setOpen = (open) => {
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
