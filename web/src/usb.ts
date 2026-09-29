import { apiSend } from "./api.ts";
import { clearFormBanner, errorMessage, onClick, showFormBanner } from "./dom.ts";
import { libraryRootForSave } from "./jobs.ts";
import { applyState } from "./shell.ts";
import { S } from "./state.ts";
import type { AppSnapshot, DeviceRow } from "./types.ts";

/** One selectable preset folder in the USB file-transfer folder picker (UI-only catalog, not
 * backend data — restores the two device-specific presets that shipped in the pre-TypeScript
 * `app.js` but were dropped when this module was split out during the TypeScript migration). */
interface UftFolderPreset {
	id: string;
	label: string;
}

const UFT_ANDROID_FOLDERS: UftFolderPreset[] = [
	{ id: "download", label: "Download" },
	{ id: "documents", label: "Documents" },
	{ id: "dcim", label: "Camera (DCIM)" },
	{ id: "pictures", label: "Pictures" },
	{ id: "movies", label: "Movies" },
	{ id: "music", label: "Music" },
];
const UFT_IPHONE_FOLDERS: UftFolderPreset[] = [{ id: "dcim", label: "Camera (DCIM)" }];

/** device_id -> label cache for the USB file-transfer device picker, refreshed by
 * `refreshUsbTransferDevices` and read by `updateUsbTransferDeviceStatus`/`pushUsbTransferSettingsWithExtras`. */
let uftDeviceLabels: Record<string, string> = {};

function selectedUsbTransferMethod(): string {
	const active = document.querySelector("#view-usb-file-transfer .connection-toggle button.active");
	return active?.getAttribute("data-uft-method") || "adb";
}
function selectedUsbTransferFolders(): string[] {
	const boxes = document.querySelectorAll("#uft-folder-picker input[data-folder]:checked");
	const out: string[] = [];
	boxes.forEach((box) => {
		const id = box.getAttribute("data-folder");
		if (id) {
			out.push(id);
		}
	});
	return out;
}
function currentUsbExtraPaths(): string[] {
	const list = document.getElementById("uft-extra-sources");
	if (!list) {
		return [];
	}
	const out: string[] = [];
	list.querySelectorAll("li[data-extra-path]").forEach((li) => {
		const path = li.getAttribute("data-extra-path");
		if (path) {
			out.push(path);
		}
	});
	return out;
}
function extraPathKind(path: string): string {
	const name = path.split("/").pop() || path;
	return name.indexOf(".") > 0 ? "file" : "folder";
}
function renderUsbTransferExtras(paths: string[] | undefined): void {
	const list = document.getElementById("uft-extra-sources");
	if (!list) {
		return;
	}
	list.innerHTML = "";
	const items = paths ?? [];
	if (!items.length) {
		list.hidden = true;
		return;
	}
	list.hidden = false;
	items.forEach((path) => {
		const li = document.createElement("li");
		li.setAttribute("data-extra-path", path);
		const name = document.createElement("span");
		name.className = "uft-extra-name";
		name.textContent = path;
		const kind = document.createElement("span");
		kind.className = "uft-extra-kind";
		kind.textContent = extraPathKind(path);
		const remove = document.createElement("button");
		remove.type = "button";
		remove.className = "btn-uft-extra-remove";
		remove.textContent = "Remove";
		remove.setAttribute("aria-label", "Remove " + path);
		remove.addEventListener("click", () => {
			const next = currentUsbExtraPaths().filter((p) => p !== path);
			pushUsbTransferSettingsWithExtras(next);
		});
		li.appendChild(name);
		li.appendChild(kind);
		li.appendChild(remove);
		list.appendChild(li);
	});
}
function rebuildUsbTransferFolders(method: string, selected: string[] | undefined, available?: string[] | null): void {
	const picker = document.getElementById("uft-folder-picker");
	const emptyHint = document.getElementById("uft-presets-empty");
	if (!picker) {
		return;
	}
	let catalog = method === "afc" ? UFT_IPHONE_FOLDERS.slice() : UFT_ANDROID_FOLDERS.slice();
	let filtered = false;
	if (Array.isArray(available)) {
		filtered = true;
		catalog = catalog.filter((item) => available.includes(item.id));
	}
	const selectedSet: Record<string, boolean> = {};
	(selected ?? []).forEach((id) => {
		selectedSet[id] = true;
	});
	picker.innerHTML = '<legend class="sr-only">Device folders that exist on this phone</legend>';
	catalog.forEach((item) => {
		const label = document.createElement("label");
		const input = document.createElement("input");
		input.type = "checkbox";
		input.setAttribute("data-folder", item.id);
		input.checked = !!selectedSet[item.id];
		input.addEventListener("change", () => {
			pushUsbTransferSettings();
		});
		label.appendChild(input);
		label.appendChild(document.createTextNode(" " + item.label));
		picker.appendChild(label);
	});
	const showEmpty = filtered && catalog.length === 0;
	picker.hidden = showEmpty;
	if (emptyHint) {
		emptyHint.classList.toggle("panel-hidden", !showEmpty);
	}
}
function syncUsbTransferBrowseUi(next: AppSnapshot): void {
	const browse = next.usb_transfer_browse;
	const btnFiles = document.getElementById("btn-uft-add-files");
	const btnFolder = document.getElementById("btn-uft-add-folder");
	const hint = document.getElementById("uft-browse-unavailable");
	const mountOk = !!browse?.mount_available;
	if (btnFiles instanceof HTMLButtonElement) {
		btnFiles.disabled = !mountOk;
	}
	if (btnFolder instanceof HTMLButtonElement) {
		btnFolder.disabled = !mountOk;
	}
	if (hint) {
		hint.classList.toggle("panel-hidden", mountOk);
		if (browse?.hint) {
			hint.textContent = browse.hint;
		}
	}
}
function syncUsbTransferConnectionButtons(method: string): void {
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach((btn) => {
		btn.classList.toggle("active", btn.getAttribute("data-uft-method") === method);
	});
}
function updateUsbTransferDeviceStatus(next: AppSnapshot): void {
	const root = document.getElementById("uft-device-status");
	const textEl = document.getElementById("uft-device-status-text");
	if (!root || !textEl) {
		return;
	}
	const method = next.connection_method || "adb";
	const methodLabel = method === "afc" ? "iPhone USB" : method === "adb" ? "ADB" : method.toUpperCase();
	const label = next.device_id ? uftDeviceLabels[next.device_id] : undefined;
	if (next.device_id && (label || next.device_label)) {
		root.classList.add("connected");
		root.classList.remove("disconnected");
		textEl.textContent = (label || next.device_label) + " · Connected via " + methodLabel;
	} else {
		root.classList.remove("connected");
		root.classList.add("disconnected");
		textEl.textContent = "No device found · Check USB and " + methodLabel + " setup";
	}
}
function refreshUsbTransferDevices(method: string): Promise<void> {
	return apiSend<DeviceRow[]>("GET", "/api/devices?connection_method=" + encodeURIComponent(method || "adb"))
		.then((devices) => {
			uftDeviceLabels = {};
			const sel = document.getElementById("uft-select-device");
			if (!(sel instanceof HTMLSelectElement)) {
				return undefined;
			}
			const previous = sel.value;
			sel.innerHTML = "";
			const empty = document.createElement("option");
			empty.value = "";
			empty.textContent = devices.length ? "Select device" : "No device";
			sel.appendChild(empty);
			devices.forEach((d) => {
				uftDeviceLabels[d.device_id] = d.label;
				const opt = document.createElement("option");
				opt.value = d.device_id;
				opt.textContent = d.label;
				sel.appendChild(opt);
			});
			if (previous && uftDeviceLabels[previous]) {
				sel.value = previous;
			} else if (S.state?.device_id && uftDeviceLabels[S.state.device_id]) {
				sel.value = S.state.device_id;
			} else if (devices.length) {
				sel.value = devices[0]?.device_id ?? "";
			}
			if (S.state) {
				const selLabel = uftDeviceLabels[sel.value];
				updateUsbTransferDeviceStatus({
					...S.state,
					device_id: sel.value || S.state.device_id || "",
					device_label: selLabel || S.state.device_label || "",
				});
			}
			if (sel.value && sel.value !== (S.state?.device_id || "")) {
				return pushUsbTransferSettings().then(() => undefined);
			}
			return undefined;
		})
		.catch((err: unknown) => {
			uftDeviceLabels = {};
			const sel = document.getElementById("uft-select-device");
			if (sel instanceof HTMLSelectElement) {
				sel.innerHTML = '<option value="">No device</option>';
			}
			showFormBanner(errorMessage(err, "Could not list devices."), "uft-form-banner");
		});
}
function pushUsbTransferSettings(): Promise<AppSnapshot> {
	return pushUsbTransferSettingsWithExtras(currentUsbExtraPaths());
}
function pushUsbTransferSettingsWithExtras(extras: string[]): Promise<AppSnapshot> {
	const sel = document.getElementById("uft-select-device");
	const deviceId = sel instanceof HTMLSelectElement ? sel.value : "";
	const method = selectedUsbTransferMethod();
	const body: Record<string, unknown> = {
		library_root: libraryRootForSave(),
		ui_mode: S.uiMode,
		connection_method: method,
		transfer_mode: document.getElementById("uft-chip-move")?.classList.contains("selected") ? "move" : "copy",
		device_id: deviceId,
		device_label: uftDeviceLabels[deviceId] || "",
		transfer_folders: selectedUsbTransferFolders(),
		transfer_extra_paths: extras || [],
	};
	return apiSend<AppSnapshot>("PUT", "/api/settings", body)
		.then((data) => {
			clearFormBanner("uft-form-banner");
			applyState(data);
			return data;
		})
		.catch((err: unknown) => {
			showFormBanner(errorMessage(err, "Could not save settings."), "uft-form-banner");
			throw err;
		});
}
function updateUsbTransferUi(next: AppSnapshot): void {
	if (!document.getElementById("view-usb-file-transfer") || !next.usb_transfer) {
		return;
	}
	const method = next.connection_method || "adb";
	const dest = document.getElementById("uft-dest-path");
	const banner = document.getElementById("uft-iphone-limit-banner");
	const chipCopy = document.getElementById("uft-chip-copy");
	const chipMove = document.getElementById("uft-chip-move");
	const sel = document.getElementById("uft-select-device");
	const phase = next.usb_transfer.phase;
	const progress = next.usb_transfer.progress ?? { completed: 0, total: 0, percent: 0 };
	const statusText = document.getElementById("uft-status-text");
	const bar = document.getElementById("uft-progress");
	const fill = document.getElementById("uft-progress-fill");
	const countLine = document.getElementById("uft-count-line");
	const countText = document.getElementById("uft-count-text");
	const actions = next.usb_transfer_actions ?? {};
	const btnStart = document.getElementById("btn-uft-start");
	const btnPause = document.getElementById("btn-uft-pause");
	const btnResume = document.getElementById("btn-uft-resume");
	const btnStop = document.getElementById("btn-uft-stop");
	const openWrap = document.getElementById("uft-open-folder-wrap");
	const showProgress = phase === "running" || phase === "paused" || phase === "done" || phase === "stopped";
	const transferActive = phase === "running" || phase === "paused";
	const available = next.usb_transfer_available_folders;
	const availableKey = Array.isArray(available) ? available.slice().sort().join(",") : "all";
	if (next.active_module === "usb_file_transfer") {
		syncUsbTransferConnectionButtons(method);
		if (S.uftFoldersMethod !== method || S.uftAvailableFoldersKey !== availableKey) {
			rebuildUsbTransferFolders(method, next.transfer_folders ?? [], available);
			S.uftFoldersMethod = method;
			S.uftAvailableFoldersKey = availableKey;
			refreshUsbTransferDevices(method);
		} else {
			document.querySelectorAll("#uft-folder-picker input[data-folder]").forEach((box) => {
				if (box instanceof HTMLInputElement) {
					const id = box.getAttribute("data-folder");
					box.checked = !!id && (next.transfer_folders ?? []).includes(id);
				}
			});
		}
		renderUsbTransferExtras(next.transfer_extra_paths ?? []);
		syncUsbTransferBrowseUi(next);
		if (dest instanceof HTMLInputElement) {
			dest.value = next.documents_receive_root_display || next.documents_receive_root || "";
		}
		if (banner) {
			banner.hidden = !next.usb_transfer_iphone_limit;
		}
		if (chipCopy && chipMove) {
			chipCopy.classList.toggle("selected", next.transfer_mode !== "move");
			chipMove.classList.toggle("selected", next.transfer_mode === "move");
		}
		updateUsbTransferDeviceStatus(next);
		if (sel instanceof HTMLSelectElement && next.device_id && uftDeviceLabels[next.device_id]) {
			sel.value = next.device_id;
		}
	}
	if (statusText) {
		if (phase === "running") {
			statusText.textContent = "Transferring… " + progress.percent + "%";
		} else if (phase === "paused") {
			statusText.textContent = "Paused — " + progress.percent + "%";
		} else if (phase === "done") {
			statusText.textContent = "Done: " + progress.completed + " files";
		} else if (phase === "stopped") {
			statusText.textContent = "Stopped: " + progress.completed + " files";
		} else if (phase === "error") {
			statusText.textContent = next.last_error || "Error";
		} else {
			statusText.textContent = "Not started";
		}
	}
	if (bar) {
		bar.hidden = !showProgress;
		bar.setAttribute("aria-valuenow", String(progress.percent || 0));
	}
	if (fill) {
		fill.style.width = (progress.percent || 0) + "%";
	}
	if (countLine) {
		countLine.hidden = !showProgress;
	}
	if (countText) {
		countText.textContent = progress.completed + " files transferred";
	}
	if (btnStart instanceof HTMLButtonElement) {
		btnStart.disabled = !actions.start;
		btnStart.hidden = phase === "running" || phase === "paused";
	}
	if (btnPause instanceof HTMLButtonElement) {
		btnPause.hidden = !actions.pause;
		btnPause.disabled = !actions.pause;
	}
	if (btnResume instanceof HTMLButtonElement) {
		btnResume.hidden = !actions.resume;
		btnResume.disabled = !actions.resume;
	}
	if (btnStop instanceof HTMLButtonElement) {
		btnStop.hidden = !actions.stop;
		btnStop.disabled = !actions.stop;
	}
	if (openWrap) {
		openWrap.classList.toggle("panel-hidden", !next.usb_transfer_show_open_folder);
	}
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach((btn) => {
		if (btn instanceof HTMLButtonElement) {
			btn.disabled = transferActive;
		}
	});
	document
		.querySelectorAll("#uft-folder-picker input, #uft-select-device, #uft-chip-copy, #uft-chip-move")
		.forEach((el) => {
			if (el instanceof HTMLInputElement || el instanceof HTMLSelectElement || el instanceof HTMLButtonElement) {
				el.disabled = transferActive;
			}
		});
}
function bindUsbDesktop(): void {
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach((btn) => {
		btn.addEventListener("click", () => {
			const method = btn.getAttribute("data-uft-method") || "adb";
			syncUsbTransferConnectionButtons(method);
			S.uftFoldersMethod = "";
			S.uftAvailableFoldersKey = "";
			refreshUsbTransferDevices(method).then(() => pushUsbTransferSettingsWithExtras([]));
		});
	});
	onClick("uft-chip-copy", () => {
		document.getElementById("uft-chip-copy")?.classList.add("selected");
		document.getElementById("uft-chip-move")?.classList.remove("selected");
		pushUsbTransferSettings();
	});
	onClick("uft-chip-move", () => {
		document.getElementById("uft-chip-move")?.classList.add("selected");
		document.getElementById("uft-chip-copy")?.classList.remove("selected");
		pushUsbTransferSettings();
	});
	const uftSelect = document.getElementById("uft-select-device");
	if (uftSelect) {
		uftSelect.addEventListener("change", () => {
			pushUsbTransferSettings();
		});
	}
	function ensureUsbMountForPicks(): Promise<string> {
		const browse = S.state?.usb_transfer_browse;
		if (browse?.mount_root) {
			return Promise.resolve(browse.mount_root);
		}
		if (!browse?.mount_available) {
			showFormBanner(
				browse?.hint || "Add files/folder needs adbfs on PATH for ADB (or iPhone ifuse). Desktop app only.",
				"uft-form-banner",
			);
			return Promise.reject(new Error("mount unavailable"));
		}
		return apiSend<AppSnapshot>("POST", "/api/usb-transfer/mount").then((data) => {
			applyState(data);
			const next = data.usb_transfer_browse;
			if (!next?.mount_root) {
				throw new Error(next?.hint || "Could not mount phone for Add files/folder.");
			}
			return next.mount_root;
		});
	}
	function postUsbHostPicks(paths: string[] | null | undefined): Promise<AppSnapshot | null> {
		const filtered = Array.isArray(paths) ? paths.filter(Boolean) : [];
		if (!filtered.length) {
			return Promise.resolve(null);
		}
		return apiSend<AppSnapshot>("POST", "/api/usb-transfer/extras", { host_paths: filtered }).then((data) => {
			clearFormBanner("uft-form-banner");
			applyState(data);
			return data;
		});
	}
	onClick("btn-uft-add-files", () => {
		if (!window.pywebview?.api?.choose_device_files) {
			showFormBanner("Add files works in the desktop app.", "uft-form-banner");
			return;
		}
		ensureUsbMountForPicks()
			.then((mount) => Promise.resolve(window.pywebview?.api?.choose_device_files?.(mount)))
			.then(postUsbHostPicks)
			.catch((err: unknown) => {
				if (err instanceof Error && err.message === "mount unavailable") {
					return;
				}
				showFormBanner(errorMessage(err, "Could not add files."), "uft-form-banner");
			});
	});
	onClick("btn-uft-add-folder", () => {
		if (!window.pywebview?.api?.choose_device_folder) {
			showFormBanner("Add folder works in the desktop app.", "uft-form-banner");
			return;
		}
		ensureUsbMountForPicks()
			.then((mount) => Promise.resolve(window.pywebview?.api?.choose_device_folder?.(mount)))
			.then((folder) => postUsbHostPicks(folder ? [folder] : []))
			.catch((err: unknown) => {
				if (err instanceof Error && err.message === "mount unavailable") {
					return;
				}
				showFormBanner(errorMessage(err, "Could not add folder."), "uft-form-banner");
			});
	});
	onClick("btn-uft-start", () => {
		pushUsbTransferSettings()
			.then(() => apiSend<AppSnapshot>("POST", "/api/usb-transfer/start"))
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Transfer could not start."), "uft-form-banner");
				if (S.state) {
					updateUsbTransferUi(S.state);
				}
			});
	});
	onClick("btn-uft-pause", () => {
		apiSend<AppSnapshot>("POST", "/api/usb-transfer/pause")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Pause failed."), "uft-form-banner");
			});
	});
	onClick("btn-uft-resume", () => {
		apiSend<AppSnapshot>("POST", "/api/usb-transfer/resume")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Resume failed."), "uft-form-banner");
			});
	});
	onClick("btn-uft-stop", () => {
		apiSend<AppSnapshot>("POST", "/api/usb-transfer/stop")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Stop failed."), "uft-form-banner");
			});
	});
	onClick("btn-uft-open-folder", () => {
		apiSend("POST", "/api/documents/open-folder").catch((err: unknown) => {
			showFormBanner(errorMessage(err, "Could not open destination folder."), "uft-form-banner");
		});
	});
}

export {
	bindUsbDesktop,
	currentUsbExtraPaths,
	extraPathKind,
	pushUsbTransferSettings,
	pushUsbTransferSettingsWithExtras,
	rebuildUsbTransferFolders,
	refreshUsbTransferDevices,
	renderUsbTransferExtras,
	selectedUsbTransferFolders,
	selectedUsbTransferMethod,
	syncUsbTransferBrowseUi,
	syncUsbTransferConnectionButtons,
	updateUsbTransferDeviceStatus,
	updateUsbTransferUi,
};
