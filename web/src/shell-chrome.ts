// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R } from "./state.js";

function bindDesktopChrome() {
	document.querySelectorAll(".view-tabs button").forEach(function (btn) {
		btn.addEventListener("click", function () {
			var v = btn.getAttribute("data-view");
			if (v === "home") {
				R.goHomeHub();
				return;
			}
			R.showView(v);
		});
	});
	document.querySelectorAll("[data-module]").forEach(function (tile) {
		tile.addEventListener("click", function () {
			var moduleId = tile.getAttribute("data-module");
			if (moduleId) {
				R.enterModule(moduleId);
			}
		});
	});
	document.querySelectorAll(".breadcrumb-home").forEach(function (btn) {
		btn.addEventListener("click", function () {
			R.goHomeHub();
		});
	});
	R.onClick("btn-open-documents-folder", function () {
		R.api("POST", "/api/documents/open-folder").catch(function (err) {
			R.showFormBanner(err.message || "Could not open documents folder.");
		});
	});
	R.onClick("btn-transfer-open-documents", function () {
		R.api("POST", "/api/documents/open-folder").catch(function (err) {
			window.alert(err.message || "Could not open documents folder.");
		});
	});
	function bindInfoToggle(btnId, panelId) {
		var btn = document.getElementById(btnId);
		var panel = document.getElementById(panelId);
		if (!btn || !panel) {
			return;
		}
		btn.addEventListener("click", function () {
			var open = panel.classList.toggle("visible");
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
R.bindDesktopChrome = bindDesktopChrome;

export { bindDesktopChrome };
