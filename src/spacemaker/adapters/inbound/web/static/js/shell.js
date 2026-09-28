// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function reloadStaleShell(serverVersion) {
	var slug = String(serverVersion || "").replace(/\./g, "-");
	var next = "/?_shell=" + encodeURIComponent(slug || "latest") + "&_=" + String(Date.now());
	location.replace(next);
}
function healIfStaleShell(settings) {
	if (!R.isDesktopShell() || !settings) {
		return;
	}
	var pageVersion = window.SPACEMAKER_UI_SHELL_VERSION || "";
	var serverVersion = settings.ui_shell_version || "";
	if (pageVersion && serverVersion && pageVersion === serverVersion) {
		R.clearHomeFormBanner();
		return;
	}
	// Stale WebEngine document vs live server — pull latest once, no user-facing panic.
	var reloadKey = "spacemaker-shell-reload:" + serverVersion;
	try {
		if (!sessionStorage.getItem(reloadKey)) {
			sessionStorage.setItem(reloadKey, "1");
			reloadStaleShell(serverVersion);
			return;
		}
	} catch (_err) {
		reloadStaleShell(serverVersion);
		return;
	}
	R.clearHomeFormBanner();
}
function syncActiveModuleView(next) {
	if (!R.isDesktopShell() || !next || R.toolsBlockMainApp(next)) {
		return;
	}
	var active = document.querySelector(".screen.active");
	if (!active?.id) {
		return;
	}
	if (active.id === "view-components") {
		return;
	}
	var currentId = active.id.replace(/^view-/, "");
	if (currentId === "gallery" || currentId === "gallery-item" || currentId === "settings" || currentId === "legal") {
		return;
	}
	var target = !next.active_module || next.active_module === "home" ? "home" : moduleToViewId(next.active_module);
	if (currentId !== target) {
		showView(target, { skipHistory: true });
	}
}
function moduleToViewId(module) {
	switch (module) {
		case "photo_backup":
			return "easy";
		case "usb_photo_backup":
			return "wizard";
		case "usb_file_transfer":
			return "usb-file-transfer";
		case "receive_files":
			return "receive-files";
		case "send_files":
			return "send-files";
		case "transfer_files":
			return "transfer-files";
		default:
			return "home";
	}
}
function homeViewId() {
	if (!S.state?.active_module || S.state.active_module === "home") {
		return "home";
	}
	return moduleToViewId(S.state.active_module);
}
function isMainHubView(resolved) {
	return (
		resolved === "home" ||
		resolved === "easy" ||
		resolved === "wizard" ||
		resolved === "usb-file-transfer" ||
		resolved === "receive-files" ||
		resolved === "send-files" ||
		resolved === "transfer-files"
	);
}
function enterModule(moduleId) {
	return R.api("POST", "/api/module/enter", { module: moduleId })
		.then(applyState)
		.then(function () {
			showView(moduleToViewId(moduleId));
		})
		.catch(function (err) {
			R.showFormBanner(err.message || "Could not open this module.");
		});
}
function goHomeHub() {
	return R.api("POST", "/api/module/home")
		.then(applyState)
		.then(function () {
			showView("home");
		})
		.catch(function (err) {
			R.showFormBanner(err.message || "Could not return to Home.");
		});
}
function easyFileCountLabel(count, singular, plural) {
	if (count === 1) {
		return "1 " + singular;
	}
	return count + " " + plural;
}
function _setUiMode(mode, options) {
	options = options || {};
	S.uiMode = mode === "advanced" ? "advanced" : "easy";
	var btnEasy = document.getElementById("btn-ui-easy");
	var btnAdvanced = document.getElementById("btn-ui-advanced");
	var active;
	if (btnEasy) {
		btnEasy.classList.toggle("active", S.uiMode === "easy");
	}
	if (btnAdvanced) {
		btnAdvanced.classList.toggle("active", S.uiMode === "advanced");
	}
	if (!options.skipViewSwitch && !R.toolsBlockMainApp(S.state)) {
		active = document.querySelector(".screen.active");
		if (active && (active.id === "view-easy" || active.id === "view-wizard")) {
			showView("home", { skipHistory: true });
		}
	}
}
function setUiModeFromState(next) {
	S.uiMode = next.ui_mode === "advanced" ? "advanced" : "easy";
}
function pathForMainView(viewId) {
	if (viewId === "gallery") {
		return "/gallery";
	}
	if (viewId === "home" || viewId === "easy" || viewId === "wizard") {
		return "/";
	}
	return null;
}
function showView(viewId, options) {
	var path;
	var itemPath;
	var resolved = viewId;
	options = options || {};
	if (viewId === "home") {
		resolved = "home";
	}
	document.querySelectorAll(".screen").forEach(function (s) {
		s.classList.remove("active");
	});
	document.getElementById("view-" + resolved).classList.add("active");
	R.syncGalleryPhoneHelpVisibility(resolved);
	if (isMainHubView(resolved) || resolved === "gallery" || resolved === "gallery-item") {
		document.querySelectorAll(".view-tabs button").forEach(function (b) {
			var tab = b.getAttribute("data-view");
			b.classList.toggle(
				"active",
				(tab === "gallery" && resolved.indexOf("gallery") === 0) || (tab === "home" && isMainHubView(resolved)),
			);
		});
		if (isMainHubView(resolved) || resolved === "gallery") {
			if (resolved === "gallery") {
				R.loadGallery();
			}
		}
		if (!options.skipHistory) {
			if (resolved === "gallery-item" && S.galleryItemPath) {
				itemPath = "/gallery/item/" + encodeURI(S.galleryItemPath);
				if (location.pathname !== itemPath) {
					history.pushState({ view: "gallery-item", path: S.galleryItemPath }, "", itemPath);
				}
			} else {
				path = pathForMainView(isMainHubView(resolved) ? "home" : resolved);
				if (path !== null && location.pathname !== path) {
					history.pushState({ view: resolved }, "", path);
				}
			}
		}
	} else if (resolved === "settings" || resolved === "settings-tools" || resolved === "legal") {
		document.querySelectorAll(".view-tabs button").forEach(function (b) {
			b.classList.toggle("active", b.getAttribute("data-view") === "settings");
		});
	}
}
function routeFromPath() {
	var itemPath = R.galleryItemPathFromLocation();
	if (itemPath) {
		R.showGalleryItem(itemPath, { skipHistory: true });
		return;
	}
	if (location.pathname === "/gallery") {
		showView("gallery", { skipHistory: true });
		return;
	}
	if (location.pathname === "/" || location.pathname === "") {
		showView(homeViewId(), { skipHistory: true });
	}
}
window.addEventListener("popstate", function () {
	routeFromPath();
});
function applyState(next) {
	S.state = next;
	if (R.isMobileGalleryShell()) {
		return;
	}
	R.updateAboutMeta(next);
	setUiModeFromState(next);
	R.maybeShowMissingTools(next);
	R.syncConnectionButtons(next.connection_method || "wifi");
	var lib = document.getElementById("input-library-root");
	if (lib && document.activeElement !== lib) {
		lib.value = next.library_root || "";
	}
	R.syncFolderCheckboxes(next.source_folders);
	if ((next.connection_method || "wifi") !== "wifi") {
		R.updateDeviceStatus(next);
	}
	R.updateWifiUploadPanel(next);
	R.updateExtractUi(next);
	R.updateConvertUi(next);
	R.updateVisualizeUi(next);
	R.updateWarnings(next);
	R.updateEasyUi(next);
	R.updateReceiveUi(next);
	R.updateSendUi(next);
	R.updateUsbTransferUi(next);
	R.updateTransferUi(next);
	if (next.managed_tools) {
		R.renderComponentsList(next.managed_tools);
	}
	R.maybeShowComponentsScreen(next);
	if (R.toolsBlockMainApp(next)) {
		return;
	}
	syncActiveModuleView(next);
	R.validateStep1Form(false);
	R.updateExtractButtons(next);
}
function isGalleryEntryPath() {
	return location.pathname === "/gallery" || location.pathname.indexOf("/gallery/item/") === 0;
}
function connectWs() {
	var proto = location.protocol === "https:" ? "wss" : "ws";
	var ws = new WebSocket(proto + "://" + location.host + "/ws");
	ws.onmessage = function (ev) {
		var msg = JSON.parse(ev.data);
		if (msg.type === "state") {
			applyState(msg.state);
		}
		if (msg.type === "gallery_export") {
			R.applyGalleryExport(msg.export);
		}
	};
	ws.onclose = function () {
		setTimeout(connectWs, 2000);
	};
}
function bootstrapMobileGalleryShell() {
	R.bindGalleryUi();
	routeFromPath();
	connectWs();
}
function bootstrapDesktopShell() {
	R.bindDesktopChrome();
	R.bindUsbDesktop();
	R.bindLanDesktop();
	R.bindSettingsDesktop();
	R.bindHomeDesktop();
	R.bootDesktopSession();
}
R.reloadStaleShell = reloadStaleShell;
R.healIfStaleShell = healIfStaleShell;
R.syncActiveModuleView = syncActiveModuleView;
R.moduleToViewId = moduleToViewId;
R.homeViewId = homeViewId;
R.isMainHubView = isMainHubView;
R.enterModule = enterModule;
R.goHomeHub = goHomeHub;
R.easyFileCountLabel = easyFileCountLabel;
R._setUiMode = _setUiMode;
R.setUiModeFromState = setUiModeFromState;
R.pathForMainView = pathForMainView;
R.showView = showView;
R.routeFromPath = routeFromPath;
R.applyState = applyState;
R.isGalleryEntryPath = isGalleryEntryPath;
R.connectWs = connectWs;
R.bootstrapMobileGalleryShell = bootstrapMobileGalleryShell;
R.bootstrapDesktopShell = bootstrapDesktopShell;

export {
	_setUiMode,
	applyState,
	bootstrapDesktopShell,
	bootstrapMobileGalleryShell,
	connectWs,
	easyFileCountLabel,
	enterModule,
	goHomeHub,
	healIfStaleShell,
	homeViewId,
	isGalleryEntryPath,
	isMainHubView,
	moduleToViewId,
	pathForMainView,
	reloadStaleShell,
	routeFromPath,
	setUiModeFromState,
	showView,
	syncActiveModuleView,
};
