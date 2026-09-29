import { apiSend } from "./api.js";
import { errorMessage, showFormBanner } from "./dom.js";
import { loadServerInfo } from "./gallery-timeline.js";
import { selectedConnectionMethod, validateStep1Form } from "./home.js";
import { loadDevices, updateExtractButtons } from "./jobs.js";
import { maybeShowComponentsScreen, runComponentsEnsure, toolsBlockMainApp } from "./settings.js";
import {
	applyState,
	connectWs,
	healIfStaleShell,
	isGalleryEntryPath,
	moduleToViewId,
	routeFromPath,
	showView,
} from "./shell.js";
import { S } from "./state.js";

function bootDesktopSession() {
	apiSend("GET", "/api/defaults")
		.then((defaults) => {
			S.defaultLibraryRoot = defaults.default_library_root || "";
			const lib = document.getElementById("input-library-root");
			if (lib instanceof HTMLInputElement) {
				lib.placeholder = S.defaultLibraryRoot;
			}
			return apiSend("GET", "/api/settings");
		})
		.then((settings) => {
			if (!settings.library_root && S.defaultLibraryRoot) {
				settings.library_root = S.defaultLibraryRoot;
				return apiSend("PUT", "/api/settings", {
					library_root: S.defaultLibraryRoot,
					ui_mode: settings.ui_mode || "easy",
					connection_method: settings.connection_method,
					transfer_mode: settings.transfer_mode,
					device_id: settings.device_id,
					device_label: settings.device_label,
					source_folders: settings.source_folders || ["dcim", "pictures", "movies"],
				});
			}
			return settings;
		})
		.then(applyState)
		.then(() => {
			healIfStaleShell(S.state);
			if (S.state && toolsBlockMainApp(S.state)) {
				maybeShowComponentsScreen(S.state);
				return runComponentsEnsure()
					.then(() => apiSend("GET", "/api/settings"))
					.then(applyState);
			}
			return null;
		})
		.then(() => {
			if (S.state && toolsBlockMainApp(S.state)) {
				maybeShowComponentsScreen(S.state);
				return null;
			}
			routeFromPath();
			if (isGalleryEntryPath()) {
				return null;
			}
			if (S.state?.active_module && S.state.active_module !== "home") {
				showView(moduleToViewId(S.state.active_module), { skipHistory: true });
			} else {
				showView("home", { skipHistory: true });
			}
			if (S.state && S.state.active_module === "usb_photo_backup" && selectedConnectionMethod() !== "wifi") {
				return loadDevices();
			}
			return null;
		})
		.then(() => {
			if (isGalleryEntryPath()) {
				return;
			}
			validateStep1Form(true);
			if (S.state) {
				updateExtractButtons(S.state);
			}
		})
		.then(loadServerInfo)
		.catch((err) => {
			showFormBanner(errorMessage(err, "Failed to load settings."));
		});
	connectWs();
}

export { bootDesktopSession };
