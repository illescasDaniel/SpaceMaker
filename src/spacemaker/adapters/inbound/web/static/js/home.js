// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function clearHomeFormBanner() {
	var homeBanner = document.getElementById("home-form-banner");
	if (homeBanner) {
		homeBanner.hidden = true;
		homeBanner.textContent = "";
	}
}
function selectedConnectionMethod() {
	var btnWifi = document.getElementById("btn-conn-wifi");
	if (!btnWifi) {
		return "wifi";
	}
	if (btnWifi.classList.contains("active")) {
		return "wifi";
	}
	if (document.getElementById("btn-conn-adb").classList.contains("active")) {
		return "adb";
	}
	if (document.getElementById("btn-conn-afc").classList.contains("active")) {
		return "afc";
	}
	return "wifi";
}
function validateStep1Form(showFieldErrors) {
	var lib = document.getElementById("input-library-root");
	var sel = document.getElementById("select-device");
	var libraryPath = lib ? lib.value.trim() : "";
	if (!libraryPath && S.state && S.state.library_root) {
		libraryPath = S.state.library_root;
	}
	var folders = selectedFolders();
	var method = selectedConnectionMethod();
	var deviceOk = method === "wifi" || !!sel?.value;
	var libraryOk = R.isAbsolutePath(libraryPath);
	var foldersOk = method === "wifi" || folders.length > 0;
	var libErr = document.getElementById("library-root-error");
	if (showFieldErrors && lib) {
		lib.classList.toggle("field-invalid", !libraryOk);
		lib.setAttribute("aria-invalid", libraryOk ? "false" : "true");
	}
	if (libErr) {
		if (!libraryOk && showFieldErrors) {
			libErr.hidden = false;
			libErr.textContent = libraryPath
				? "Enter a full absolute path (e.g. " + S.defaultLibraryRoot + ")."
				: "Choose a library folder with Browse or enter an absolute path.";
		} else {
			libErr.hidden = true;
		}
	}
	S.formValidation = {
		ok: libraryOk && deviceOk && foldersOk,
		library: libraryOk ? "" : "library",
		device: deviceOk ? "" : "device",
		folders: foldersOk ? "" : "folders",
	};
	return S.formValidation;
}
function monthName(n) {
	return [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	][n - 1];
}
function connectionLabel(method) {
	if (method === "wifi") {
		return "Wi‑Fi";
	}
	if (method === "adb") {
		return "ADB";
	}
	if (method === "afc") {
		return "iPhone USB";
	}
	return "ADB";
}
function applyConnectionPanels(method) {
	var isWifi = method === "wifi";
	document.getElementById("panel-usb").classList.toggle("panel-hidden", isWifi);
	document.getElementById("panel-wifi").classList.toggle("panel-hidden", !isWifi);
	var chipMove = document.getElementById("chip-move");
	var chipCopy = document.getElementById("chip-copy");
	var moveHint = document.getElementById("move-wifi-hint");
	if (isWifi) {
		chipMove.classList.add("disabled");
		chipMove.disabled = true;
		chipCopy.classList.add("selected");
		chipMove.classList.remove("selected");
		if (moveHint) {
			moveHint.hidden = false;
		}
	} else {
		chipMove.classList.remove("disabled");
		chipMove.disabled = false;
		if (moveHint) {
			moveHint.hidden = true;
		}
	}
}
function syncConnectionButtons(method) {
	document.getElementById("btn-conn-wifi").classList.toggle("active", method === "wifi");
	document.getElementById("btn-conn-adb").classList.toggle("active", method === "adb");
	document.getElementById("btn-conn-afc").classList.toggle("active", method === "afc");
	applyConnectionPanels(method);
}
function updateWifiUploadPanel(next) {
	var wifi = next.wifi_upload || {};
	var idle = document.getElementById("wifi-idle-hint");
	var live = document.getElementById("wifi-live-receive");
	var urlInput = document.getElementById("wifi-upload-url");
	var qrImg = document.getElementById("wifi-upload-qr");
	var wizardLibraryHint = document.getElementById("wizard-library-hint");
	var libDisplay = next.library_root_display || next.library_root;
	if (!idle || !live) {
		return;
	}
	if (wizardLibraryHint && libDisplay && (next.connection_method || "") === "wifi") {
		wizardLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
	} else if (wizardLibraryHint) {
		wizardLibraryHint.textContent = "";
	}
	R.setQrUrlField("wifi-qr-url-copy", wifi.upload_url || "");
	if (wifi.active) {
		idle.classList.add("panel-hidden");
		live.classList.remove("panel-hidden");
		if (urlInput) {
			urlInput.value = wifi.upload_url || "";
		}
		R.setQrImageSrc(qrImg, wifi.qr_url, "wifi-upload-qr");
	} else {
		idle.classList.remove("panel-hidden");
		live.classList.add("panel-hidden");
	}
}
function selectedFolders() {
	var boxes = document.querySelectorAll("#folder-picker input[type=checkbox]");
	var out = [];
	boxes.forEach(function (box) {
		if (box.checked && box.dataset.folder) {
			out.push(box.dataset.folder);
		}
	});
	return out;
}
function syncFolderCheckboxes(folders) {
	var set = new Set(folders || []);
	document.querySelectorAll("#folder-picker input[type=checkbox]").forEach(function (box) {
		if (box.dataset.folder) {
			box.checked = set.has(box.dataset.folder);
		}
	});
}
function updateDeviceStatus(next) {
	var root = document.getElementById("device-status");
	var textEl = document.getElementById("device-status-text");
	var name = "";
	if (!root || !textEl) {
		return;
	}
	var method = connectionLabel(next.connection_method);
	if (next.device_id && S.deviceLabels[next.device_id]) {
		name = S.deviceLabels[next.device_id];
		root.classList.add("connected");
		root.classList.remove("disconnected");
		textEl.textContent = name + " · Connected via " + method;
	} else {
		root.classList.remove("connected");
		root.classList.add("disconnected");
		textEl.textContent = "No device found · Check USB and " + method + " setup";
	}
}
function maybeShowMissingTools(next) {
	var missing = next.missing_tools || [];
	if (!missing.length) {
		return;
	}
	var banner = document.getElementById("form-banner");
	if (banner && !banner.hidden) {
		return;
	}
	R.showFormBanner(
		"Some components are missing (" + missing.join(", ") + "). Open Components setup or install them on your PATH.",
	);
}
function updateEasyUi(next) {
	var wifi = next.wifi_upload || {};
	var uploadQr = document.getElementById("easy-upload-qr");
	var uploadWait = document.getElementById("easy-upload-wait");
	var transferStatus = document.getElementById("easy-transfer-status");
	var transferFill = document.getElementById("easy-transfer-fill");
	var convertStatus = document.getElementById("easy-convert-status");
	var convertFill = document.getElementById("easy-convert-fill");
	var convertProgressBlock = document.getElementById("easy-convert-progress-block");
	var compressOffStatus = document.getElementById("easy-compress-off-status");
	var compressCheckbox = document.getElementById("easy-compress-checkbox");
	var compressLabel = document.getElementById("easy-compress-pref-label");
	var compressToolsHint = document.getElementById("easy-compress-tools-hint");
	var viewGalleryWrap = document.getElementById("easy-view-gallery-wrap");
	var processed = next.library_counts?.processed || 0;
	var compress = next.compress_media || {};
	var compressOn = compress.enabled !== false;
	var compressControlEnabled = compress.control_enabled !== false;
	var toolsAvailable = compress.tools_available !== false;
	var ep = next.extract.progress || { completed: 0, percent: 0 };
	var cp = next.convert.progress || { completed: 0, total: 0, percent: 0 };
	var photoLibraryHint = document.getElementById("photo-library-hint");
	var libDisplay = next.library_root_display || next.library_root;
	var transferPct;
	var issues;
	var errN;
	var invN;
	var parts;
	if (photoLibraryHint && libDisplay) {
		photoLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
	}
	if (compressCheckbox && document.activeElement !== compressCheckbox) {
		compressCheckbox.checked = compressOn;
		compressCheckbox.disabled = !compressControlEnabled;
	}
	if (compressLabel) {
		compressLabel.classList.toggle("is-disabled", !compressControlEnabled);
	}
	if (compressToolsHint) {
		compressToolsHint.classList.toggle("panel-hidden", toolsAvailable);
	}
	if (convertProgressBlock) {
		convertProgressBlock.classList.toggle("panel-hidden", !compressOn);
	}
	if (compressOffStatus) {
		compressOffStatus.classList.toggle("panel-hidden", compressOn);
	}
	R.setQrUrlField("easy-qr-url", wifi.upload_url || "");
	if (wifi.active && uploadQr) {
		uploadQr.hidden = false;
		R.setQrImageSrc(uploadQr, wifi.qr_url, "easy-upload-qr");
		if (uploadWait) {
			uploadWait.hidden = true;
		}
	} else {
		if (uploadQr) {
			uploadQr.hidden = true;
		}
		if (uploadWait) {
			uploadWait.hidden = false;
			uploadWait.textContent =
				next.extract.phase === "running" || next.extract.phase === "paused"
					? "Preparing upload QR…"
					: "Waiting to start Wi‑Fi receive…";
		}
	}
	if (transferStatus) {
		transferStatus.textContent = R.easyFileCountLabel(ep.completed, "file received", "files received");
	}
	if (transferFill) {
		transferPct = ep.total > 0 ? ep.percent : ep.completed > 0 ? 100 : 0;
		transferFill.style.width = transferPct + "%";
	}
	if (convertStatus) {
		if (next.convert.phase === "running") {
			convertStatus.textContent = "In progress — " + cp.completed + " / " + cp.total + " (" + cp.percent + "%)";
		} else if (next.convert.phase === "error") {
			convertStatus.textContent = "Failed — " + (next.last_error || "see Advanced for details");
		} else if (next.last_error) {
			convertStatus.textContent = next.last_error;
		} else if (next.convert.phase === "done" && cp.total > 0) {
			convertStatus.textContent = "Completed — " + cp.completed + " file(s)";
		} else if (processed > 0) {
			convertStatus.textContent = R.easyFileCountLabel(
				processed,
				"file converted, waiting for more",
				"files converted, waiting for more",
			);
		} else {
			convertStatus.textContent = "Waiting for files";
		}
	}
	if (convertFill) {
		convertFill.style.width = (next.convert.phase === "running" ? cp.percent : 0) + "%";
	}
	if (viewGalleryWrap) {
		viewGalleryWrap.classList.toggle("panel-hidden", processed <= 0);
	}
	var importIssues = document.getElementById("easy-import-issues");
	if (importIssues) {
		issues = next.image_import_issues || {};
		errN = issues.errors || 0;
		invN = issues.invalid || 0;
		parts = [];
		if (compressOn && errN > 0) {
			parts.push(errN + (errN === 1 ? " image failed to convert" : " images failed to convert"));
		}
		if (compressOn && invN > 0) {
			parts.push(invN + (invN === 1 ? " unsupported image" : " unsupported images"));
		}
		if (parts.length) {
			importIssues.textContent = parts.join(" · ");
			importIssues.classList.remove("panel-hidden");
		} else {
			importIssues.textContent = "";
			importIssues.classList.add("panel-hidden");
		}
	}
}
function updateAboutMeta(next) {
	var line = document.getElementById("about-app-meta");
	if (!line || !next) {
		return;
	}
	var ver = next.app_version || "";
	var author = next.app_author || "";
	var contact = next.app_contact || "";
	var parts = ["SpaceMaker"];
	if (ver) {
		parts[0] += " " + ver;
	}
	if (author) {
		parts.push(author);
	}
	line.textContent = parts.join(" · ");
	var link = document.getElementById("about-contact-link");
	if (link && contact) {
		link.href = "mailto:" + contact;
		link.textContent = contact;
	}
}
R.clearHomeFormBanner = clearHomeFormBanner;
R.selectedConnectionMethod = selectedConnectionMethod;
R.validateStep1Form = validateStep1Form;
R.monthName = monthName;
R.connectionLabel = connectionLabel;
R.applyConnectionPanels = applyConnectionPanels;
R.syncConnectionButtons = syncConnectionButtons;
R.updateWifiUploadPanel = updateWifiUploadPanel;
R.selectedFolders = selectedFolders;
R.syncFolderCheckboxes = syncFolderCheckboxes;
R.updateDeviceStatus = updateDeviceStatus;
R.maybeShowMissingTools = maybeShowMissingTools;
R.updateEasyUi = updateEasyUi;
R.updateAboutMeta = updateAboutMeta;

export {
	applyConnectionPanels,
	clearHomeFormBanner,
	connectionLabel,
	maybeShowMissingTools,
	monthName,
	selectedConnectionMethod,
	selectedFolders,
	syncConnectionButtons,
	syncFolderCheckboxes,
	updateAboutMeta,
	updateDeviceStatus,
	updateEasyUi,
	updateWifiUploadPanel,
	validateStep1Form,
};
