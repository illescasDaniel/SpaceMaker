import { apiSend } from "./api.js";
import { errorMessage, onClick, showFormBanner } from "./dom.js";
import { bindInfoPanels } from "./info-panels.js";
import { enterModule, goHomeHub, showView } from "./shell.js";
import { bindUrlFields } from "./url-field.js";

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
	bindInfoPanels(document);
	bindUrlFields(document);
}

export { bindDesktopChrome };
