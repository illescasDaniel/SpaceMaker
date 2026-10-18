/** Every `.info-btn[aria-controls]` toggles its `.info-panel` through the shared `.visible` class. */
function setOpen(btn, panel, open) {
	panel.classList.toggle("visible", open);
	panel.setAttribute("aria-hidden", open ? "false" : "true");
	btn.setAttribute("aria-expanded", open ? "true" : "false");
}
function closeOpenPanels(root) {
	let first = null;
	root.querySelectorAll('.info-btn[aria-expanded="true"][aria-controls]').forEach((btn) => {
		const panel = document.getElementById(btn.getAttribute("aria-controls") ?? "");
		if (panel) {
			setOpen(btn, panel, false);
		}
		first ??= btn;
	});
	first?.focus();
}
export function bindInfoPanels(root = document) {
	root.querySelectorAll(".info-btn[aria-controls]").forEach((btn) => {
		btn.addEventListener("click", () => {
			const panel = document.getElementById(btn.getAttribute("aria-controls") ?? "");
			if (panel) {
				setOpen(btn, panel, !panel.classList.contains("visible"));
			}
		});
	});
	document.addEventListener("keydown", (ev) => {
		if (ev.key === "Escape") {
			closeOpenPanels(root);
		}
	});
}
