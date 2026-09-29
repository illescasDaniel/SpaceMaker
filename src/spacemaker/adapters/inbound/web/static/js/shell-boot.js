// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function bootDesktopSession() {
	R.api("GET", "/api/defaults")
		.then(function (defaults) {
			S.defaultLibraryRoot = defaults.default_library_root || "";
			var lib = document.getElementById("input-library-root");
			if (lib) {
				lib.placeholder = S.defaultLibraryRoot;
			}
			return R.api("GET", "/api/settings");
		})
		.then(function (settings) {
			if (!settings.library_root && S.defaultLibraryRoot) {
				settings.library_root = S.defaultLibraryRoot;
				return R.api("PUT", "/api/settings", {
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
		.then(R.applyState)
		.then(function () {
			R.healIfStaleShell(S.state);
			if (S.state && R.toolsBlockMainApp(S.state)) {
				R.maybeShowComponentsScreen(S.state);
				return R.runComponentsEnsure()
					.then(function () {
						return R.api("GET", "/api/settings");
					})
					.then(R.applyState);
			}
			return null;
		})
		.then(function () {
			if (S.state && R.toolsBlockMainApp(S.state)) {
				R.maybeShowComponentsScreen(S.state);
				return null;
			}
			R.routeFromPath();
			if (R.isGalleryEntryPath()) {
				return null;
			}
			if (S.state?.active_module && S.state.active_module !== "home") {
				R.showView(R.moduleToViewId(S.state.active_module), { skipHistory: true });
			} else {
				R.showView("home", { skipHistory: true });
			}
			if (S.state && S.state.active_module === "usb_photo_backup" && R.selectedConnectionMethod() !== "wifi") {
				return R.loadDevices();
			}
			return null;
		})
		.then(function () {
			if (R.isGalleryEntryPath()) {
				return null;
			}
			R.validateStep1Form(true);
			if (S.state) {
				R.updateExtractButtons(S.state);
			}
		})
		.then(R.loadServerInfo)
		.catch(function (err) {
			R.showFormBanner(err.message || "Failed to load settings.");
		});
	R.connectWs();
}
R.bootDesktopSession = bootDesktopSession;

export { bootDesktopSession };
