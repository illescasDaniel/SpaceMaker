import { apiSend } from "./api.js";
import { errorMessage, onClick, showFormBanner } from "./dom.js";
import { enterModule, goHomeHub, showView } from "./shell.js";

function bindDesktopChrome() {
	document.querySelectorAll(".view-tabs button").forEach((btn) => {
		btn.addEventListener("click", () => {
			const v = btn.getAttribute("data-view");
			if (v === "home") {
				goHomeHub();
				return;
			}
			if (v) {
				showView(v);
			}
		});
	});
	document.querySelectorAll("[data-module]").forEach((tile) => {
		tile.addEventListener("click", () => {
			const moduleId = tile.getAttribute("data-module");
			if (moduleId) {
				enterModule(moduleId);
			}
		});
	});
	document.querySelectorAll(".breadcrumb-home").forEach((btn) => {
		btn.addEventListener("click", () => {
			goHomeHub();
		});
	});
	onClick("btn-open-documents-folder", () => {
		apiSend("POST", "/api/documents/open-folder").catch((err) => {
			showFormBanner(errorMessage(err, "Could not open documents folder."));
		});
	});
	onClick("btn-transfer-open-documents", () => {
		apiSend("POST", "/api/documents/open-folder").catch((err) => {
			window.alert(errorMessage(err, "Could not open documents folder."));
		});
	});
	function bindInfoToggle(btnId, panelId) {
		const btn = document.getElementById(btnId);
		const panel = document.getElementById(panelId);
		if (!btn || !panel) {
			return;
		}
		btn.addEventListener("click", () => {
			const open = panel.classList.toggle("visible");
			btn.setAttribute("aria-expanded", open ? "true" : "false");
			panel.setAttribute("aria-hidden", open ? "false" : "true");
		});
	}
	bindInfoToggle("btn-uft-connection-info", "uft-connection-info-panel");
	bindInfoToggle("btn-uft-folders-info", "uft-folders-info-panel");
	bindInfoToggle("btn-uft-dest-info", "uft-dest-info-panel");
	bindInfoToggle("btn-uft-mode-info", "uft-mode-info-panel");
	bindInfoToggle("btn-uft-actions-info", "uft-actions-info-panel");
}

export { bindDesktopChrome };
