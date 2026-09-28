// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function selectedUsbTransferMethod() {
	var active = document.querySelector("#view-usb-file-transfer .connection-toggle button.active");
	return active?.getAttribute("data-uft-method") || "adb";
}
function selectedUsbTransferFolders() {
	var boxes = document.querySelectorAll("#uft-folder-picker input[data-folder]:checked");
	var out = [];
	boxes.forEach(function (box) {
		out.push(box.getAttribute("data-folder"));
	});
	return out;
}
function currentUsbExtraPaths() {
	var list = document.getElementById("uft-extra-sources");
	if (!list) {
		return [];
	}
	var out = [];
	list.querySelectorAll("li[data-extra-path]").forEach(function (li) {
		out.push(li.getAttribute("data-extra-path"));
	});
	return out;
}
function extraPathKind(path) {
	var name = (path || "").split("/").pop() || path;
	return name.indexOf(".") > 0 ? "file" : "folder";
}
function renderUsbTransferExtras(paths) {
	var list = document.getElementById("uft-extra-sources");
	if (!list) {
		return;
	}
	list.innerHTML = "";
	var items = paths || [];
	if (!items.length) {
		list.hidden = true;
		return;
	}
	list.hidden = false;
	items.forEach(function (path) {
		var li = document.createElement("li");
		li.setAttribute("data-extra-path", path);
		var name = document.createElement("span");
		name.className = "uft-extra-name";
		name.textContent = path;
		var kind = document.createElement("span");
		kind.className = "uft-extra-kind";
		kind.textContent = extraPathKind(path);
		var remove = document.createElement("button");
		remove.type = "button";
		remove.className = "btn-uft-extra-remove";
		remove.textContent = "Remove";
		remove.setAttribute("aria-label", "Remove " + path);
		remove.addEventListener("click", function () {
			var next = currentUsbExtraPaths().filter(function (p) {
				return p !== path;
			});
			pushUsbTransferSettingsWithExtras(next);
		});
		li.appendChild(name);
		li.appendChild(kind);
		li.appendChild(remove);
		list.appendChild(li);
	});
}
function rebuildUsbTransferFolders(method, selected, available) {
	var picker = document.getElementById("uft-folder-picker");
	var emptyHint = document.getElementById("uft-presets-empty");
	if (!picker) {
		return;
	}
	var catalog = method === "afc" ? UFT_IPHONE_FOLDERS.slice() : UFT_ANDROID_FOLDERS.slice();
	var filtered = false;
	if (Array.isArray(available)) {
		filtered = true;
		catalog = catalog.filter(function (item) {
			return available.indexOf(item.id) >= 0;
		});
	}
	var selectedSet = {};
	(selected || []).forEach(function (id) {
		selectedSet[id] = true;
	});
	picker.innerHTML = '<legend class="sr-only">Device folders that exist on this phone</legend>';
	catalog.forEach(function (item) {
		var label = document.createElement("label");
		var input = document.createElement("input");
		input.type = "checkbox";
		input.setAttribute("data-folder", item.id);
		input.checked = !!selectedSet[item.id];
		input.addEventListener("change", function () {
			pushUsbTransferSettings();
		});
		label.appendChild(input);
		label.appendChild(document.createTextNode(" " + item.label));
		picker.appendChild(label);
	});
	var showEmpty = filtered && catalog.length === 0;
	picker.hidden = showEmpty;
	if (emptyHint) {
		emptyHint.classList.toggle("panel-hidden", !showEmpty);
	}
}
function syncUsbTransferBrowseUi(next) {
	var browse = next.usb_transfer_browse || {};
	var btnFiles = document.getElementById("btn-uft-add-files");
	var btnFolder = document.getElementById("btn-uft-add-folder");
	var hint = document.getElementById("uft-browse-unavailable");
	var mountOk = !!browse.mount_available;
	if (btnFiles) {
		btnFiles.disabled = !mountOk;
	}
	if (btnFolder) {
		btnFolder.disabled = !mountOk;
	}
	if (hint) {
		hint.classList.toggle("panel-hidden", mountOk);
		if (browse.hint) {
			hint.textContent = browse.hint;
		}
	}
}
function syncUsbTransferConnectionButtons(method) {
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach(function (btn) {
		btn.classList.toggle("active", btn.getAttribute("data-uft-method") === method);
	});
}
function updateUsbTransferDeviceStatus(next) {
	var root = document.getElementById("uft-device-status");
	var textEl = document.getElementById("uft-device-status-text");
	if (!root || !textEl) {
		return;
	}
	var method = next.connection_method || "adb";
	var methodLabel = method === "afc" ? "iPhone USB" : method === "adb" ? "ADB" : method.toUpperCase();
	if (next.device_id && (uftDeviceLabels[next.device_id] || next.device_label)) {
		root.classList.add("connected");
		root.classList.remove("disconnected");
		textEl.textContent = (uftDeviceLabels[next.device_id] || next.device_label) + " · Connected via " + methodLabel;
	} else {
		root.classList.remove("connected");
		root.classList.add("disconnected");
		textEl.textContent = "No device found · Check USB and " + methodLabel + " setup";
	}
}
function refreshUsbTransferDevices(method) {
	return R.api("GET", "/api/devices?connection_method=" + encodeURIComponent(method || "adb"))
		.then(function (devices) {
			uftDeviceLabels = {};
			var sel = document.getElementById("uft-select-device");
			if (!sel) {
				return;
			}
			var previous = sel.value;
			sel.innerHTML = "";
			var empty = document.createElement("option");
			empty.value = "";
			empty.textContent = devices.length ? "Select device" : "No device";
			sel.appendChild(empty);
			devices.forEach(function (d) {
				uftDeviceLabels[d.device_id] = d.label;
				var opt = document.createElement("option");
				opt.value = d.device_id;
				opt.textContent = d.label;
				sel.appendChild(opt);
			});
			if (previous && uftDeviceLabels[previous]) {
				sel.value = previous;
			} else if (S.state?.device_id && uftDeviceLabels[S.state.device_id]) {
				sel.value = S.state.device_id;
			} else if (devices.length) {
				sel.value = devices[0].device_id;
			}
			if (S.state) {
				updateUsbTransferDeviceStatus(
					Object.assign({}, S.state, {
						device_id: sel.value || S.state.device_id,
						device_label: uftDeviceLabels[sel.value] || S.state.device_label,
					}),
				);
			}
			if (sel.value && sel.value !== (S.state?.device_id || "")) {
				return pushUsbTransferSettings();
			}
		})
		.catch(function (err) {
			uftDeviceLabels = {};
			var sel = document.getElementById("uft-select-device");
			if (sel) {
				sel.innerHTML = '<option value="">No device</option>';
			}
			R.showFormBanner(err.message || "Could not list devices.", "uft-form-banner");
		});
}
function pushUsbTransferSettings() {
	return pushUsbTransferSettingsWithExtras(currentUsbExtraPaths());
}
function pushUsbTransferSettingsWithExtras(extras) {
	var sel = document.getElementById("uft-select-device");
	var deviceId = sel ? sel.value : "";
	var method = selectedUsbTransferMethod();
	var body = {
		library_root: R.libraryRootForSave(),
		ui_mode: S.uiMode,
		connection_method: method,
		transfer_mode: document.getElementById("uft-chip-move")?.classList.contains("selected") ? "move" : "copy",
		device_id: deviceId,
		device_label: uftDeviceLabels[deviceId] || "",
		transfer_folders: selectedUsbTransferFolders(),
		transfer_extra_paths: extras || [],
	};
	return R.api("PUT", "/api/settings", body)
		.then(function (data) {
			R.clearFormBanner("uft-form-banner");
			R.applyState(data);
			return data;
		})
		.catch(function (err) {
			R.showFormBanner(err.message || "Could not save settings.", "uft-form-banner");
			throw err;
		});
}
function updateUsbTransferUi(next) {
	if (!document.getElementById("view-usb-file-transfer") || !next.usb_transfer) {
		return;
	}
	var method = next.connection_method || "adb";
	var dest = document.getElementById("uft-dest-path");
	var banner = document.getElementById("uft-iphone-limit-banner");
	var chipCopy = document.getElementById("uft-chip-copy");
	var chipMove = document.getElementById("uft-chip-move");
	var sel = document.getElementById("uft-select-device");
	var phase = next.usb_transfer.phase;
	var progress = next.usb_transfer.progress || { completed: 0, total: 0, percent: 0 };
	var statusText = document.getElementById("uft-status-text");
	var bar = document.getElementById("uft-progress");
	var fill = document.getElementById("uft-progress-fill");
	var countLine = document.getElementById("uft-count-line");
	var countText = document.getElementById("uft-count-text");
	var actions = next.usb_transfer_actions || {};
	var btnStart = document.getElementById("btn-uft-start");
	var btnPause = document.getElementById("btn-uft-pause");
	var btnResume = document.getElementById("btn-uft-resume");
	var btnStop = document.getElementById("btn-uft-stop");
	var openWrap = document.getElementById("uft-open-folder-wrap");
	var showProgress = phase === "running" || phase === "paused" || phase === "done" || phase === "stopped";
	var transferActive = phase === "running" || phase === "paused";
	var available = next.usb_transfer_available_folders;
	var availableKey = Array.isArray(available) ? available.slice().sort().join(",") : "all";
	if (next.active_module === "usb_file_transfer") {
		syncUsbTransferConnectionButtons(method);
		if (S.uftFoldersMethod !== method || S.uftAvailableFoldersKey !== availableKey) {
			rebuildUsbTransferFolders(method, next.transfer_folders || [], available);
			S.uftFoldersMethod = method;
			S.uftAvailableFoldersKey = availableKey;
			refreshUsbTransferDevices(method);
		} else {
			document.querySelectorAll("#uft-folder-picker input[data-folder]").forEach(function (box) {
				var id = box.getAttribute("data-folder");
				box.checked = (next.transfer_folders || []).indexOf(id) >= 0;
			});
		}
		renderUsbTransferExtras(next.transfer_extra_paths || []);
		syncUsbTransferBrowseUi(next);
		if (dest) {
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
		if (sel && next.device_id && uftDeviceLabels[next.device_id]) {
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
	if (btnStart) {
		btnStart.disabled = !actions.start;
		btnStart.hidden = phase === "running" || phase === "paused";
	}
	if (btnPause) {
		btnPause.hidden = !actions.pause;
		btnPause.disabled = !actions.pause;
	}
	if (btnResume) {
		btnResume.hidden = !actions.resume;
		btnResume.disabled = !actions.resume;
	}
	if (btnStop) {
		btnStop.hidden = !actions.stop;
		btnStop.disabled = !actions.stop;
	}
	if (openWrap) {
		openWrap.classList.toggle("panel-hidden", !next.usb_transfer_show_open_folder);
	}
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach(function (btn) {
		btn.disabled = transferActive;
	});
	document
		.querySelectorAll("#uft-folder-picker input, #uft-select-device, #uft-chip-copy, #uft-chip-move")
		.forEach(function (el) {
			el.disabled = transferActive;
		});
}
function bindUsbDesktop() {
	document.querySelectorAll("#view-usb-file-transfer .connection-toggle button").forEach(function (btn) {
		btn.addEventListener("click", function () {
			var method = btn.getAttribute("data-uft-method");
			syncUsbTransferConnectionButtons(method);
			S.uftFoldersMethod = "";
			S.uftAvailableFoldersKey = "";
			refreshUsbTransferDevices(method).then(function () {
				return pushUsbTransferSettingsWithExtras([]);
			});
		});
	});
	R.onClick("uft-chip-copy", function () {
		document.getElementById("uft-chip-copy")?.classList.add("selected");
		document.getElementById("uft-chip-move")?.classList.remove("selected");
		pushUsbTransferSettings();
	});
	R.onClick("uft-chip-move", function () {
		document.getElementById("uft-chip-move")?.classList.add("selected");
		document.getElementById("uft-chip-copy")?.classList.remove("selected");
		pushUsbTransferSettings();
	});
	var uftSelect = document.getElementById("uft-select-device");
	if (uftSelect) {
		uftSelect.addEventListener("change", pushUsbTransferSettings);
	}
	function ensureUsbMountForPicks() {
		var browse = S.state?.usb_transfer_browse || {};
		if (!browse.mount_available && !browse.mount_root) {
			R.showFormBanner(
				browse.hint || "Add files/folder needs adbfs on PATH for ADB (or iPhone ifuse). Desktop app only.",
				"uft-form-banner",
			);
			return Promise.reject(new Error("mount unavailable"));
		}
		if (browse.mount_root) {
			return Promise.resolve(browse.mount_root);
		}
		return R.api("POST", "/api/usb-transfer/mount").then(function (data) {
			R.applyState(data);
			var next = data.usb_transfer_browse || {};
			if (!next.mount_root) {
				throw new Error(next.hint || "Could not mount phone for Add files/folder.");
			}
			return next.mount_root;
		});
	}
	function postUsbHostPicks(paths) {
		var filtered = Array.isArray(paths) ? paths.filter(Boolean) : [];
		if (!filtered.length) {
			return Promise.resolve(null);
		}
		return R.api("POST", "/api/usb-transfer/extras", { host_paths: filtered }).then(function (data) {
			R.clearFormBanner("uft-form-banner");
			R.applyState(data);
			return data;
		});
	}
	R.onClick("btn-uft-add-files", function () {
		if (!window.pywebview?.api?.choose_device_files) {
			R.showFormBanner("Add files works in the desktop app.", "uft-form-banner");
			return;
		}
		ensureUsbMountForPicks()
			.then(function (mount) {
				return Promise.resolve(window.pywebview.api.choose_device_files(mount));
			})
			.then(postUsbHostPicks)
			.catch(function (err) {
				if (err && err.message === "mount unavailable") {
					return;
				}
				R.showFormBanner(err.message || "Could not add files.", "uft-form-banner");
			});
	});
	R.onClick("btn-uft-add-folder", function () {
		if (!window.pywebview?.api?.choose_device_folder) {
			R.showFormBanner("Add folder works in the desktop app.", "uft-form-banner");
			return;
		}
		ensureUsbMountForPicks()
			.then(function (mount) {
				return Promise.resolve(window.pywebview.api.choose_device_folder(mount));
			})
			.then(function (folder) {
				return postUsbHostPicks(folder ? [folder] : []);
			})
			.catch(function (err) {
				if (err && err.message === "mount unavailable") {
					return;
				}
				R.showFormBanner(err.message || "Could not add folder.", "uft-form-banner");
			});
	});
	R.onClick("btn-uft-start", function () {
		pushUsbTransferSettings()
			.then(function () {
				return R.api("POST", "/api/usb-transfer/start");
			})
			.then(applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Transfer could not start.", "uft-form-banner");
				if (S.state) {
					updateUsbTransferUi(S.state);
				}
			});
	});
	R.onClick("btn-uft-pause", function () {
		R.api("POST", "/api/usb-transfer/pause")
			.then(applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Pause failed.", "uft-form-banner");
			});
	});
	R.onClick("btn-uft-resume", function () {
		R.api("POST", "/api/usb-transfer/resume")
			.then(applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Resume failed.", "uft-form-banner");
			});
	});
	R.onClick("btn-uft-stop", function () {
		R.api("POST", "/api/usb-transfer/stop")
			.then(applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Stop failed.", "uft-form-banner");
			});
	});
	R.onClick("btn-uft-open-folder", function () {
		R.api("POST", "/api/documents/open-folder").catch(function (err) {
			R.showFormBanner(err.message || "Could not open destination folder.", "uft-form-banner");
		});
	});
}
R.selectedUsbTransferMethod = selectedUsbTransferMethod;
R.selectedUsbTransferFolders = selectedUsbTransferFolders;
R.currentUsbExtraPaths = currentUsbExtraPaths;
R.extraPathKind = extraPathKind;
R.renderUsbTransferExtras = renderUsbTransferExtras;
R.rebuildUsbTransferFolders = rebuildUsbTransferFolders;
R.syncUsbTransferBrowseUi = syncUsbTransferBrowseUi;
R.syncUsbTransferConnectionButtons = syncUsbTransferConnectionButtons;
R.updateUsbTransferDeviceStatus = updateUsbTransferDeviceStatus;
R.refreshUsbTransferDevices = refreshUsbTransferDevices;
R.pushUsbTransferSettings = pushUsbTransferSettings;
R.pushUsbTransferSettingsWithExtras = pushUsbTransferSettingsWithExtras;
R.updateUsbTransferUi = updateUsbTransferUi;
R.bindUsbDesktop = bindUsbDesktop;

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
