import { isAbsolutePath, setQrImage, setQrUrlField, showFormBanner } from "./dom.ts";
import { easyFileCountLabel } from "./shell.ts";
import { S } from "./state.ts";
import type { AppSnapshot, FormValidation } from "./types.ts";

function clearHomeFormBanner(): void {
	const homeBanner = document.getElementById("home-form-banner");
	if (homeBanner) {
		homeBanner.hidden = true;
		homeBanner.textContent = "";
	}
}
function selectedConnectionMethod(): string {
	const btnWifi = document.getElementById("btn-conn-wifi");
	if (!btnWifi) {
		return "wifi";
	}
	if (btnWifi.classList.contains("active")) {
		return "wifi";
	}
	if (document.getElementById("btn-conn-adb")?.classList.contains("active")) {
		return "adb";
	}
	if (document.getElementById("btn-conn-afc")?.classList.contains("active")) {
		return "afc";
	}
	return "wifi";
}
function validateStep1Form(showFieldErrors: boolean): FormValidation {
	const lib = document.getElementById("input-library-root");
	const sel = document.getElementById("select-device");
	let libraryPath = lib instanceof HTMLInputElement ? lib.value.trim() : "";
	if (!libraryPath && S.state?.library_root) {
		libraryPath = S.state.library_root;
	}
	const folders = selectedFolders();
	const method = selectedConnectionMethod();
	const deviceOk = method === "wifi" || !!(sel instanceof HTMLSelectElement && sel.value);
	const libraryOk = isAbsolutePath(libraryPath);
	const foldersOk = method === "wifi" || folders.length > 0;
	const libErr = document.getElementById("library-root-error");
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
function monthName(n: number): string {
	const names = [
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
	];
	return names[n - 1] ?? "";
}
function connectionLabel(method: string | undefined): string {
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
function applyConnectionPanels(method: string): void {
	const isWifi = method === "wifi";
	document.getElementById("panel-usb")?.classList.toggle("panel-hidden", isWifi);
	document.getElementById("panel-wifi")?.classList.toggle("panel-hidden", !isWifi);
	const chipMove = document.getElementById("chip-move");
	const chipCopy = document.getElementById("chip-copy");
	const moveHint = document.getElementById("move-wifi-hint");
	if (isWifi) {
		chipMove?.classList.add("disabled");
		if (chipMove instanceof HTMLButtonElement) {
			chipMove.disabled = true;
		}
		chipCopy?.classList.add("selected");
		chipMove?.classList.remove("selected");
		if (moveHint) {
			moveHint.hidden = false;
		}
	} else {
		chipMove?.classList.remove("disabled");
		if (chipMove instanceof HTMLButtonElement) {
			chipMove.disabled = false;
		}
		if (moveHint) {
			moveHint.hidden = true;
		}
	}
}
function syncConnectionButtons(method: string): void {
	document.getElementById("btn-conn-wifi")?.classList.toggle("active", method === "wifi");
	document.getElementById("btn-conn-adb")?.classList.toggle("active", method === "adb");
	document.getElementById("btn-conn-afc")?.classList.toggle("active", method === "afc");
	applyConnectionPanels(method);
}
function updateWifiUploadPanel(next: AppSnapshot): void {
	const wifi = next.wifi_upload;
	const idle = document.getElementById("wifi-idle-hint");
	const live = document.getElementById("wifi-live-receive");
	const urlInput = document.getElementById("wifi-upload-url");
	const qrImg = document.getElementById("wifi-upload-qr");
	const wizardLibraryHint = document.getElementById("wizard-library-hint");
	const libDisplay = next.library_root_display || next.library_root;
	if (!idle || !live) {
		return;
	}
	if (wizardLibraryHint && libDisplay && (next.connection_method || "") === "wifi") {
		wizardLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
	} else if (wizardLibraryHint) {
		wizardLibraryHint.textContent = "";
	}
	setQrUrlField("wifi-qr-url-copy", wifi?.upload_url || "");
	if (wifi?.active) {
		idle.classList.add("panel-hidden");
		live.classList.remove("panel-hidden");
		if (urlInput instanceof HTMLInputElement) {
			urlInput.value = wifi.upload_url || "";
		}
		setQrImage(qrImg instanceof HTMLImageElement ? qrImg : null, wifi.qr_url, "wifi-upload-qr");
	} else {
		idle.classList.remove("panel-hidden");
		live.classList.add("panel-hidden");
	}
}
function selectedFolders(): string[] {
	const boxes = document.querySelectorAll("#folder-picker input[type=checkbox]");
	const out: string[] = [];
	boxes.forEach((box) => {
		if (box instanceof HTMLInputElement && box.checked && box.dataset.folder) {
			out.push(box.dataset.folder);
		}
	});
	return out;
}
function syncFolderCheckboxes(folders: string[] | undefined): void {
	const set = new Set(folders || []);
	document.querySelectorAll("#folder-picker input[type=checkbox]").forEach((box) => {
		if (box instanceof HTMLInputElement && box.dataset.folder) {
			box.checked = set.has(box.dataset.folder);
		}
	});
}
function updateDeviceStatus(next: AppSnapshot): void {
	const root = document.getElementById("device-status");
	const textEl = document.getElementById("device-status-text");
	let name = "";
	if (!root || !textEl) {
		return;
	}
	const method = connectionLabel(next.connection_method);
	const label = next.device_id ? S.deviceLabels[next.device_id] : undefined;
	if (label) {
		name = label;
		root.classList.add("connected");
		root.classList.remove("disconnected");
		textEl.textContent = name + " · Connected via " + method;
	} else {
		root.classList.remove("connected");
		root.classList.add("disconnected");
		textEl.textContent = "No device found · Check USB and " + method + " setup";
	}
}
function maybeShowMissingTools(next: AppSnapshot): void {
	const missing = next.missing_tools || [];
	if (!missing.length) {
		return;
	}
	const banner = document.getElementById("form-banner");
	if (banner && !banner.hidden) {
		return;
	}
	showFormBanner(
		"Some components are missing (" + missing.join(", ") + "). Open Components setup or install them on your PATH.",
	);
}
function updateEasyUi(next: AppSnapshot): void {
	const wifi = next.wifi_upload;
	const uploadQr = document.getElementById("easy-upload-qr");
	const uploadWait = document.getElementById("easy-upload-wait");
	const transferStatus = document.getElementById("easy-transfer-status");
	const transferFill = document.getElementById("easy-transfer-fill");
	const convertStatus = document.getElementById("easy-convert-status");
	const convertFill = document.getElementById("easy-convert-fill");
	const convertProgressBlock = document.getElementById("easy-convert-progress-block");
	const compressOffStatus = document.getElementById("easy-compress-off-status");
	const compressCheckbox = document.getElementById("easy-compress-checkbox");
	const compressLabel = document.getElementById("easy-compress-pref-label");
	const compressToolsHint = document.getElementById("easy-compress-tools-hint");
	const viewGalleryWrap = document.getElementById("easy-view-gallery-wrap");
	const processed = next.library_counts?.processed || 0;
	const compress = next.compress_media;
	const compressOn = compress?.enabled !== false;
	const compressControlEnabled = compress?.control_enabled !== false;
	const toolsAvailable = compress?.tools_available !== false;
	const ep = next.extract?.progress ?? { completed: 0, total: 0, percent: 0 };
	const cp = next.convert?.progress ?? { completed: 0, total: 0, percent: 0 };
	const photoLibraryHint = document.getElementById("photo-library-hint");
	const libDisplay = next.library_root_display || next.library_root;
	if (photoLibraryHint && libDisplay) {
		photoLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
	}
	if (compressCheckbox instanceof HTMLInputElement && document.activeElement !== compressCheckbox) {
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
	setQrUrlField("easy-qr-url", wifi?.upload_url || "");
	if (wifi?.active && uploadQr) {
		uploadQr.hidden = false;
		setQrImage(uploadQr instanceof HTMLImageElement ? uploadQr : null, wifi.qr_url, "easy-upload-qr");
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
				next.extract?.phase === "running" || next.extract?.phase === "paused"
					? "Preparing upload QR…"
					: "Waiting to start Wi‑Fi receive…";
		}
	}
	if (transferStatus) {
		transferStatus.textContent = easyFileCountLabel(ep.completed, "file received", "files received");
	}
	if (transferFill) {
		const transferPct = ep.total > 0 ? ep.percent : ep.completed > 0 ? 100 : 0;
		transferFill.style.width = transferPct + "%";
	}
	if (convertStatus) {
		if (next.convert?.phase === "running") {
			convertStatus.textContent = "In progress — " + cp.completed + " / " + cp.total + " (" + cp.percent + "%)";
		} else if (next.convert?.phase === "error") {
			convertStatus.textContent = "Failed — " + (next.last_error || "see Advanced for details");
		} else if (next.last_error) {
			convertStatus.textContent = next.last_error;
		} else if (next.convert?.phase === "done" && cp.total > 0) {
			convertStatus.textContent = "Completed — " + cp.completed + " file(s)";
		} else if (processed > 0) {
			convertStatus.textContent = easyFileCountLabel(
				processed,
				"file converted, waiting for more",
				"files converted, waiting for more",
			);
		} else {
			convertStatus.textContent = "Waiting for files";
		}
	}
	if (convertFill) {
		convertFill.style.width = (next.convert?.phase === "running" ? cp.percent : 0) + "%";
	}
	if (viewGalleryWrap) {
		viewGalleryWrap.classList.toggle("panel-hidden", processed <= 0);
	}
	const importIssues = document.getElementById("easy-import-issues");
	if (importIssues) {
		const issues = next.image_import_issues ?? { errors: 0, invalid: 0 };
		const errN = issues.errors || 0;
		const invN = issues.invalid || 0;
		const parts: string[] = [];
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
function updateAboutMeta(next: AppSnapshot | null | undefined): void {
	const line = document.getElementById("about-app-meta");
	if (!line || !next) {
		return;
	}
	const ver = next.app_version || "";
	const author = next.app_author || "";
	const contact = next.app_contact || "";
	const parts = ["SpaceMaker"];
	if (ver) {
		parts[0] += " " + ver;
	}
	if (author) {
		parts.push(author);
	}
	line.textContent = parts.join(" · ");
	const link = document.getElementById("about-contact-link");
	if (link instanceof HTMLAnchorElement && contact) {
		link.href = "mailto:" + contact;
		link.textContent = contact;
	}
}

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
