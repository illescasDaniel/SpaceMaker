import { apiSend } from "./api.js";
import { clearFormBanner, errorMessage, setStatusLine, showFormBanner } from "./dom.js";
import { selectedConnectionMethod, selectedFolders, updateDeviceStatus, updateWifiUploadPanel } from "./home.js";
import { applyState } from "./shell.js";
import { S } from "./state.js";

function updateExtractUi(next) {
	const status = document.getElementById("extract-status");
	const bar = document.getElementById("extract-progress");
	const fill = document.getElementById("extract-progress-fill");
	const counts = document.getElementById("extract-counts");
	if (!status) {
		return;
	}
	const phase = next.extract?.phase ?? "";
	const p = next.extract?.progress ?? { completed: 0, total: 0, percent: 0 };
	setStatusLine(status, extractPhaseLabel(phase, p, !!next.extract_stopping));
	if (fill) {
		fill.style.width = p.percent + "%";
	}
	if (bar) {
		bar.setAttribute("aria-valuenow", String(p.percent));
	}
	if (counts) {
		if (
			(next.connection_method || "") === "wifi" &&
			(phase === "running" || phase === "paused" || phase === "stopped" || phase === "done")
		) {
			counts.textContent = p.completed + " files received";
		} else {
			counts.textContent = p.completed + " / " + p.total + " files";
		}
	}
	const extractActive = phase === "running" || phase === "paused";
	document
		.querySelectorAll("#folder-picker input, #select-device, #input-library-root, #chip-copy, #chip-move")
		.forEach((el) => {
			if (el instanceof HTMLInputElement || el instanceof HTMLSelectElement || el instanceof HTMLButtonElement) {
				el.disabled = extractActive;
			}
		});
	const btnConnWifi = document.getElementById("btn-conn-wifi");
	const btnConnAdb = document.getElementById("btn-conn-adb");
	const btnConnAfc = document.getElementById("btn-conn-afc");
	if (btnConnWifi instanceof HTMLButtonElement) {
		btnConnWifi.disabled = extractActive;
	}
	if (btnConnAdb instanceof HTMLButtonElement) {
		btnConnAdb.disabled = extractActive;
	}
	if (btnConnAfc instanceof HTMLButtonElement) {
		btnConnAfc.disabled = extractActive;
	}
	updateWifiUploadPanel(next);
}
function extractPhaseLabel(phase, progress, extractStopping) {
	const method = S.state?.connection_method;
	if (method === "wifi" && phase === "running") {
		return "Receiving uploads…";
	}
	if (method === "wifi" && phase === "paused") {
		return "Paused — not accepting uploads";
	}
	if (extractStopping && phase === "running") {
		return "Stopping — finishing current file…";
	}
	if (phase === "running") {
		return "In progress — " + progress.percent + "%";
	}
	if (phase === "paused") {
		return "Paused — " + progress.percent + "%";
	}
	if (phase === "done") {
		return "Completed — " + progress.completed + " files";
	}
	if (phase === "stopped") {
		return "Stopped — " + progress.completed + " files done";
	}
	if (phase === "error") {
		return "Error";
	}
	return "Ready";
}
function extractIsActive(next) {
	const phase = next?.extract ? next.extract.phase : "";
	return phase === "running" || phase === "paused";
}
function canStartConvert(next) {
	if (next.can_start_convert) {
		return true;
	}
	const counts = next.library_counts;
	return (counts?.originals || 0) > 0;
}
function updateExtractButtons(next) {
	const controls = next.extract_controls || {};
	const valid = S.formValidation.ok;
	const extractActive = extractIsActive(next);
	const btnStart = document.getElementById("btn-start-extract");
	const btnPause = document.getElementById("btn-pause-extract");
	const btnResume = document.getElementById("btn-resume-extract");
	const btnStop = document.getElementById("btn-stop-extract");
	if (btnStart instanceof HTMLButtonElement) {
		btnStart.hidden = extractActive;
		btnStart.disabled = extractActive || !controls.start || !valid;
	}
	if (btnPause instanceof HTMLButtonElement) {
		btnPause.hidden = !controls.pause;
		btnPause.disabled = !controls.pause;
	}
	if (btnResume instanceof HTMLButtonElement) {
		btnResume.hidden = !controls.resume;
		btnResume.disabled = !controls.resume;
	}
	if (btnStop instanceof HTMLButtonElement) {
		btnStop.hidden = !controls.stop;
		btnStop.disabled = !controls.stop;
	}
}
function updateVisualizeUi(next) {
	const card = document.getElementById("step3-card");
	const status = document.getElementById("visualize-status");
	const btn = document.getElementById("btn-open-gallery");
	if (!card || !status) {
		return;
	}
	const viz = next.visualize;
	const enabled = !!viz?.enabled;
	card.classList.toggle("disabled", !enabled);
	card.classList.toggle("done", enabled && viz?.phase === "completed");
	setStatusLine(status, viz?.status_text || "Not started");
	if (btn instanceof HTMLButtonElement) {
		btn.disabled = !enabled;
	}
}
function updateConvertUi(next) {
	const status = document.getElementById("convert-status");
	const fill = document.getElementById("convert-progress-fill");
	const btn = document.getElementById("btn-start-convert");
	const btnStop = document.getElementById("btn-stop-convert");
	const convertControls = next.convert_controls || {};
	if (!status) {
		return;
	}
	const p = next.convert?.progress ?? { completed: 0, total: 0, percent: 0 };
	const convertPhase = next.convert?.phase ?? "";
	const extractPhase = next.extract?.phase ?? "";
	const ready = canStartConvert(next);
	const originals = next.library_counts?.originals || 0;
	const bucketErrorCount = next.library_counts?.error || 0;
	const bucketInvalidCount = next.library_counts?.invalid || 0;
	if (convertPhase === "running") {
		setStatusLine(status, "In progress — " + p.completed + " / " + p.total + " (" + p.percent + "%)");
	} else if (convertPhase === "stopped") {
		setStatusLine(status, "Stopped — " + p.completed + " / " + p.total + " processed");
	} else if (convertPhase === "error") {
		setStatusLine(status, "Failed — " + (next.last_error || "Convert stopped unexpectedly."));
	} else if (convertPhase === "done" && p.total > 0) {
		if (bucketErrorCount > 0 || bucketInvalidCount > 0) {
			setStatusLine(
				status,
				"Completed with issues — " +
					(next.last_error || bucketErrorCount + " in error/, " + bucketInvalidCount + " in invalid/"),
			);
		} else {
			setStatusLine(status, "Completed — " + p.completed + " file(s) processed");
		}
	} else if ((extractPhase === "running" || extractPhase === "paused") && ready) {
		setStatusLine(
			status,
			"Extract active — " + originals + " file(s) in originals/; Start convert will stop extract and convert them",
		);
	} else if (extractPhase === "running" || extractPhase === "paused") {
		setStatusLine(status, "Waiting — add files to originals/ to convert during extract");
	} else if (extractPhase === "stopped") {
		setStatusLine(status, "Extract stopped — you can convert files already in originals/");
	} else if (!ready) {
		setStatusLine(status, "Add files to originals/ first (" + originals + " found at library root)");
	} else {
		setStatusLine(status, "Ready — " + originals + " file(s) in originals/");
	}
	if (fill) {
		fill.style.width = p.percent + "%";
	}
	if (btn instanceof HTMLButtonElement) {
		btn.hidden = convertPhase === "running";
		btn.disabled = !ready || convertPhase === "running";
	}
	if (btnStop instanceof HTMLButtonElement) {
		btnStop.hidden = !convertControls.stop;
		btnStop.disabled = !convertControls.stop;
	}
	if (next.last_error && (convertPhase === "error" || (convertPhase === "done" && bucketErrorCount > 0))) {
		showFormBanner(next.last_error);
	}
}
function updateWarnings(next) {
	const counts = next.library_counts || {};
	const errBox = document.getElementById("alert-error");
	const invBox = document.getElementById("alert-invalid");
	const errCount = counts.error || 0;
	const invCount = counts.invalid || 0;
	if (errBox) {
		errBox.hidden = errCount <= 0;
		errBox.style.display = errCount <= 0 ? "none" : "";
	}
	if (invBox) {
		invBox.hidden = invCount <= 0;
		invBox.style.display = invCount <= 0 ? "none" : "";
	}
	const errN = document.getElementById("alert-error-count");
	const invN = document.getElementById("alert-invalid-count");
	if (errN) {
		errN.textContent = String(errCount);
	}
	if (invN) {
		invN.textContent = String(invCount);
	}
	const errDetail = document.getElementById("alert-error-detail");
	if (errDetail) {
		if (errCount > 0 && next.last_error) {
			errDetail.hidden = false;
			errDetail.textContent = next.last_error;
		} else {
			errDetail.hidden = true;
			errDetail.textContent = "";
		}
	}
}
function loadDevices() {
	const method = selectedConnectionMethod();
	if (method === "wifi") {
		return Promise.resolve();
	}
	return apiSend("GET", "/api/devices?connection_method=" + method)
		.then((devices) => {
			S.deviceLabels = {};
			devices.forEach((d) => {
				S.deviceLabels[d.device_id] = d.label;
			});
			const sel = document.getElementById("select-device");
			if (!(sel instanceof HTMLSelectElement)) {
				return undefined;
			}
			const previous = sel.value;
			sel.innerHTML = "";
			devices.forEach((d) => {
				const opt = document.createElement("option");
				opt.value = d.device_id;
				opt.textContent = d.label;
				sel.appendChild(opt);
			});
			if (devices.length) {
				if (previous && S.deviceLabels[previous]) {
					sel.value = previous;
				} else if (S.state?.device_id && S.deviceLabels[S.state.device_id]) {
					sel.value = S.state.device_id;
				} else {
					sel.value = devices[0]?.device_id ?? "";
				}
				if (!S.state?.device_id) {
					return pushSettings().then(() => undefined);
				}
			}
			if (S.state) {
				updateDeviceStatus(S.state);
			}
			return undefined;
		})
		.catch((err) => {
			S.deviceLabels = {};
			const sel = document.getElementById("select-device");
			if (sel instanceof HTMLSelectElement) {
				sel.innerHTML = "";
			}
			if (S.state) {
				updateDeviceStatus(S.state);
			}
			showFormBanner(errorMessage(err, "Could not list devices."));
		});
}
function libraryRootForSave() {
	const lib = document.getElementById("input-library-root");
	let path = lib instanceof HTMLInputElement ? lib.value.trim() : "";
	if (!path && S.state?.library_root) {
		path = S.state.library_root;
	}
	if (!path && S.defaultLibraryRoot) {
		path = S.defaultLibraryRoot;
	}
	return path;
}
/** Fire-and-forget save: `pushSettings` already shows the banner, so swallow its rejection. */
function pushSettingsDetached() {
	pushSettings().catch(() => undefined);
}
function pushSettings() {
	const sel = document.getElementById("select-device");
	const modeCopy = document.getElementById("chip-copy");
	const compressCheckbox = document.getElementById("easy-compress-checkbox");
	const deviceId = sel instanceof HTMLSelectElement ? sel.value : "";
	const body = {
		library_root: libraryRootForSave(),
		ui_mode: S.uiMode,
		connection_method: selectedConnectionMethod(),
		transfer_mode: modeCopy?.classList.contains("selected") ? "copy" : "move",
		device_id: deviceId,
		device_label: S.deviceLabels[deviceId] || "",
		source_folders: selectedFolders(),
	};
	/* Only send when the control is enabled — avoid overwriting a stored
       preference while tools are unavailable (checkbox forced off). */
	if (compressCheckbox instanceof HTMLInputElement && !compressCheckbox.disabled) {
		body.compress_media = compressCheckbox.checked;
	}
	return apiSend("PUT", "/api/settings", body)
		.then((data) => {
			clearFormBanner();
			applyState(data);
			return data;
		})
		.catch((err) => {
			showFormBanner(errorMessage(err, "Could not save settings."));
			throw err;
		});
}

export {
	canStartConvert,
	extractIsActive,
	extractPhaseLabel,
	libraryRootForSave,
	loadDevices,
	pushSettings,
	pushSettingsDetached,
	updateConvertUi,
	updateExtractButtons,
	updateExtractUi,
	updateVisualizeUi,
	updateWarnings,
};
