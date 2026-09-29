import { apiSend } from "./api.js";
import { errorMessage, isDesktopShell, isMobileGalleryShell, showFormBanner } from "./dom.js";
import { bindGalleryUi } from "./gallery.js";
import {
	applyGalleryExport,
	galleryItemPathFromLocation,
	showGalleryItem,
	syncGalleryPhoneHelpVisibility,
} from "./gallery-item.js";
import { loadGallery } from "./gallery-timeline.js";
import {
	clearHomeFormBanner,
	maybeShowMissingTools,
	syncConnectionButtons,
	syncFolderCheckboxes,
	updateAboutMeta,
	updateDeviceStatus,
	updateEasyUi,
	updateWifiUploadPanel,
	validateStep1Form,
} from "./home.js";
import { bindHomeDesktop } from "./home-bind.js";
import { updateConvertUi, updateExtractButtons, updateExtractUi, updateVisualizeUi, updateWarnings } from "./jobs.js";
import { bindLanDesktop, updateReceiveUi, updateSendUi, updateTransferUi } from "./lan.js";
import { bindSettingsDesktop, maybeShowComponentsScreen, renderComponentsList, toolsBlockMainApp } from "./settings.js";
import { bootDesktopSession } from "./shell-boot.js";
import { bindDesktopChrome } from "./shell-chrome.js";
import { S } from "./state.js";
import { bindUsbDesktop, updateUsbTransferUi } from "./usb.js";

function reloadStaleShell(serverVersion) {
	const slug = serverVersion.replace(/\./g, "-");
	const next = "/?_shell=" + encodeURIComponent(slug || "latest") + "&_=" + String(Date.now());
	location.replace(next);
}
function healIfStaleShell(settings) {
	if (!isDesktopShell() || !settings) {
		return;
	}
	const pageVersion = window.SPACEMAKER_UI_SHELL_VERSION || "";
	const serverVersion = settings.ui_shell_version || "";
	if (pageVersion && serverVersion && pageVersion === serverVersion) {
		clearHomeFormBanner();
		return;
	}
	// Stale WebEngine document vs live server — pull latest once, no user-facing panic.
	const reloadKey = "spacemaker-shell-reload:" + serverVersion;
	try {
		if (!sessionStorage.getItem(reloadKey)) {
			sessionStorage.setItem(reloadKey, "1");
			reloadStaleShell(serverVersion);
			return;
		}
	} catch {
		reloadStaleShell(serverVersion);
		return;
	}
	clearHomeFormBanner();
}
function syncActiveModuleView(next) {
	if (!isDesktopShell() || !next || toolsBlockMainApp(next)) {
		return;
	}
	const active = document.querySelector(".screen.active");
	if (!active?.id) {
		return;
	}
	if (active.id === "view-components") {
		return;
	}
	const currentId = active.id.replace(/^view-/, "");
	if (currentId === "gallery" || currentId === "gallery-item" || currentId === "settings" || currentId === "legal") {
		return;
	}
	const target = !next.active_module || next.active_module === "home" ? "home" : moduleToViewId(next.active_module);
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
	return apiSend("POST", "/api/module/enter", { module: moduleId })
		.then(applyState)
		.then(() => {
			showView(moduleToViewId(moduleId));
		})
		.catch((err) => {
			showFormBanner(errorMessage(err, "Could not open this module."));
		});
}
function goHomeHub() {
	return apiSend("POST", "/api/module/home")
		.then(applyState)
		.then(() => {
			showView("home");
		})
		.catch((err) => {
			showFormBanner(errorMessage(err, "Could not return to Home."));
		});
}
function easyFileCountLabel(count, singular, plural) {
	if (count === 1) {
		return "1 " + singular;
	}
	return count + " " + plural;
}
function _setUiMode(mode, options) {
	const opts = options || {};
	S.uiMode = mode === "advanced" ? "advanced" : "easy";
	const btnEasy = document.getElementById("btn-ui-easy");
	const btnAdvanced = document.getElementById("btn-ui-advanced");
	if (btnEasy) {
		btnEasy.classList.toggle("active", S.uiMode === "easy");
	}
	if (btnAdvanced) {
		btnAdvanced.classList.toggle("active", S.uiMode === "advanced");
	}
	if (!opts.skipViewSwitch && !toolsBlockMainApp(S.state)) {
		const active = document.querySelector(".screen.active");
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
	const opts = options || {};
	const resolved = viewId === "home" ? "home" : viewId;
	document.querySelectorAll(".screen").forEach((s) => {
		s.classList.remove("active");
	});
	document.getElementById("view-" + resolved)?.classList.add("active");
	syncGalleryPhoneHelpVisibility(resolved);
	if (isMainHubView(resolved) || resolved === "gallery" || resolved === "gallery-item") {
		document.querySelectorAll(".view-tabs button").forEach((b) => {
			const tab = b.getAttribute("data-view");
			b.classList.toggle(
				"active",
				(tab === "gallery" && resolved.indexOf("gallery") === 0) || (tab === "home" && isMainHubView(resolved)),
			);
		});
		if (resolved === "gallery" && !opts.skipGalleryReload) {
			loadGallery();
		}
		if (!opts.skipHistory) {
			if (resolved === "gallery-item" && S.galleryItemPath) {
				const itemPath = "/gallery/item/" + encodeURI(S.galleryItemPath);
				if (location.pathname !== itemPath) {
					history.pushState({ view: "gallery-item", path: S.galleryItemPath }, "", itemPath);
				}
			} else {
				const path = pathForMainView(isMainHubView(resolved) ? "home" : resolved);
				if (path !== null && location.pathname !== path) {
					history.pushState({ view: resolved }, "", path);
				}
			}
		}
	} else if (resolved === "settings" || resolved === "settings-tools" || resolved === "legal") {
		document.querySelectorAll(".view-tabs button").forEach((b) => {
			b.classList.toggle("active", b.getAttribute("data-view") === "settings");
		});
	}
}
function routeFromPath() {
	const itemPath = galleryItemPathFromLocation();
	if (itemPath) {
		showGalleryItem(itemPath, { skipHistory: true });
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
window.addEventListener("popstate", () => {
	routeFromPath();
});
function applyState(next) {
	S.state = next;
	if (isMobileGalleryShell()) {
		return;
	}
	updateAboutMeta(next);
	setUiModeFromState(next);
	maybeShowMissingTools(next);
	syncConnectionButtons(next.connection_method || "wifi");
	const lib = document.getElementById("input-library-root");
	if (lib instanceof HTMLInputElement && document.activeElement !== lib) {
		lib.value = next.library_root || "";
	}
	syncFolderCheckboxes(next.source_folders);
	if ((next.connection_method || "wifi") !== "wifi") {
		updateDeviceStatus(next);
	}
	updateWifiUploadPanel(next);
	updateExtractUi(next);
	updateConvertUi(next);
	updateVisualizeUi(next);
	updateWarnings(next);
	updateEasyUi(next);
	updateReceiveUi(next);
	updateSendUi(next);
	updateUsbTransferUi(next);
	updateTransferUi(next);
	if (next.managed_tools) {
		renderComponentsList(next.managed_tools);
	}
	maybeShowComponentsScreen(next);
	if (toolsBlockMainApp(next)) {
		return;
	}
	syncActiveModuleView(next);
	validateStep1Form(false);
	updateExtractButtons(next);
}
function isGalleryEntryPath() {
	return location.pathname === "/gallery" || location.pathname.indexOf("/gallery/item/") === 0;
}
function connectWs() {
	const proto = location.protocol === "https:" ? "wss" : "ws";
	const ws = new WebSocket(proto + "://" + location.host + "/ws");
	ws.onmessage = (ev) => {
		const msg = JSON.parse(ev.data);
		if (msg.type === "state" && msg.state) {
			applyState(msg.state);
		}
		if (msg.type === "gallery_export") {
			applyGalleryExport(msg.export);
		}
	};
	ws.onclose = () => {
		setTimeout(connectWs, 2000);
	};
}
function bootstrapMobileGalleryShell() {
	bindGalleryUi();
	routeFromPath();
	connectWs();
}
function bootstrapDesktopShell() {
	bindDesktopChrome();
	bindUsbDesktop();
	bindLanDesktop();
	bindSettingsDesktop();
	bindHomeDesktop();
	bootDesktopSession();
}

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
