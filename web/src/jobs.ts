// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function updateExtractUi(next) {
	var status = document.getElementById("extract-status");
	var bar = document.getElementById("extract-progress");
	var fill = document.getElementById("extract-progress-fill");
	var counts = document.getElementById("extract-counts");
	if (!status) {
		return;
	}
	var phase = next.extract.phase;
	var p = next.extract.progress;
	R.setStatusLine(status, extractPhaseLabel(phase, p, !!next.extract_stopping));
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
	var extractActive = phase === "running" || phase === "paused";
	document
		.querySelectorAll("#folder-picker input, #select-device, #input-library-root, #chip-copy, #chip-move")
		.forEach(function (el) {
			el.disabled = extractActive;
		});
	document.getElementById("btn-conn-wifi").disabled = extractActive;
	document.getElementById("btn-conn-adb").disabled = extractActive;
	document.getElementById("btn-conn-afc").disabled = extractActive;
	R.updateWifiUploadPanel(next);
}
function extractPhaseLabel(phase, progress, extractStopping) {
	var method = S.state?.connection_method;
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
	var phase = next?.extract ? next.extract.phase : "";
	return phase === "running" || phase === "paused";
}
function canStartConvert(next) {
	if (next.can_start_convert) {
		return true;
	}
	var counts = next.library_counts || {};
	return (counts.originals || 0) > 0;
}
function updateExtractButtons(next) {
	var controls = next.extract_controls || {};
	var valid = S.formValidation.ok;
	var extractActive = extractIsActive(next);
	var btnStart = document.getElementById("btn-start-extract");
	var btnPause = document.getElementById("btn-pause-extract");
	var btnResume = document.getElementById("btn-resume-extract");
	var btnStop = document.getElementById("btn-stop-extract");
	if (btnStart) {
		btnStart.hidden = extractActive;
		btnStart.disabled = extractActive || !controls.start || !valid;
	}
	if (btnPause) {
		btnPause.hidden = !controls.pause;
		btnPause.disabled = !controls.pause;
	}
	if (btnResume) {
		btnResume.hidden = !controls.resume;
		btnResume.disabled = !controls.resume;
	}
	if (btnStop) {
		btnStop.hidden = !controls.stop;
		btnStop.disabled = !controls.stop;
	}
}
function updateVisualizeUi(next) {
	var card = document.getElementById("step3-card");
	var status = document.getElementById("visualize-status");
	var btn = document.getElementById("btn-open-gallery");
	if (!card || !status) {
		return;
	}
	var viz = next.visualize || {};
	var enabled = !!viz.enabled;
	card.classList.toggle("disabled", !enabled);
	card.classList.toggle("done", enabled && viz.phase === "completed");
	R.setStatusLine(status, viz.status_text || "Not started");
	if (btn) {
		btn.disabled = !enabled;
	}
}
function updateConvertUi(next) {
	var status = document.getElementById("convert-status");
	var fill = document.getElementById("convert-progress-fill");
	var btn = document.getElementById("btn-start-convert");
	var btnStop = document.getElementById("btn-stop-convert");
	var convertControls = next.convert_controls || {};
	if (!status) {
		return;
	}
	var p = next.convert.progress;
	var extractPhase = next.extract.phase;
	var ready = canStartConvert(next);
	var originals = next.library_counts?.originals || 0;
	var bucketErrorCount = next.library_counts?.error || 0;
	var bucketInvalidCount = next.library_counts?.invalid || 0;
	if (next.convert.phase === "running") {
		R.setStatusLine(status, "In progress — " + p.completed + " / " + p.total + " (" + p.percent + "%)");
	} else if (next.convert.phase === "stopped") {
		R.setStatusLine(status, "Stopped — " + p.completed + " / " + p.total + " processed");
	} else if (next.convert.phase === "error") {
		R.setStatusLine(status, "Failed — " + (next.last_error || "Convert stopped unexpectedly."));
	} else if (next.convert.phase === "done" && p.total > 0) {
		if (bucketErrorCount > 0 || bucketInvalidCount > 0) {
			R.setStatusLine(
				status,
				"Completed with issues — " +
					(next.last_error || bucketErrorCount + " in error/, " + bucketInvalidCount + " in invalid/"),
			);
		} else {
			R.setStatusLine(status, "Completed — " + p.completed + " file(s) processed");
		}
	} else if ((extractPhase === "running" || extractPhase === "paused") && ready) {
		R.setStatusLine(
			status,
			"Extract active — " + originals + " file(s) in originals/; Start convert will stop extract and convert them",
		);
	} else if (extractPhase === "running" || extractPhase === "paused") {
		R.setStatusLine(status, "Waiting — add files to originals/ to convert during extract");
	} else if (extractPhase === "stopped") {
		R.setStatusLine(status, "Extract stopped — you can convert files already in originals/");
	} else if (!ready) {
		R.setStatusLine(status, "Add files to originals/ first (" + originals + " found at library root)");
	} else {
		R.setStatusLine(status, "Ready — " + originals + " file(s) in originals/");
	}
	if (fill) {
		fill.style.width = p.percent + "%";
	}
	if (btn) {
		btn.hidden = next.convert.phase === "running";
		btn.disabled = !ready || next.convert.phase === "running";
	}
	if (btnStop) {
		btnStop.hidden = !convertControls.stop;
		btnStop.disabled = !convertControls.stop;
	}
	if (next.last_error && (next.convert.phase === "error" || (next.convert.phase === "done" && bucketErrorCount > 0))) {
		R.showFormBanner(next.last_error);
	}
}
function updateWarnings(next) {
	var counts = next.library_counts || {};
	var errBox = document.getElementById("alert-error");
	var invBox = document.getElementById("alert-invalid");
	var errCount = counts.error || 0;
	var invCount = counts.invalid || 0;
	if (errBox) {
		errBox.hidden = errCount <= 0;
		errBox.style.display = errCount <= 0 ? "none" : "";
	}
	if (invBox) {
		invBox.hidden = invCount <= 0;
		invBox.style.display = invCount <= 0 ? "none" : "";
	}
	var errN = document.getElementById("alert-error-count");
	var invN = document.getElementById("alert-invalid-count");
	if (errN) {
		errN.textContent = String(errCount);
	}
	if (invN) {
		invN.textContent = String(invCount);
	}
	var errDetail = document.getElementById("alert-error-detail");
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
	var method = R.selectedConnectionMethod();
	if (method === "wifi") {
		return Promise.resolve([]);
	}
	return R.api("GET", "/api/devices?connection_method=" + method)
		.then(function (devices) {
			S.deviceLabels = {};
			devices.forEach(function (d) {
				S.deviceLabels[d.device_id] = d.label;
			});
			var sel = document.getElementById("select-device");
			if (!sel) {
				return;
			}
			var previous = sel.value;
			sel.innerHTML = "";
			devices.forEach(function (d) {
				var opt = document.createElement("option");
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
					sel.value = devices[0].device_id;
				}
				if (!S.state?.device_id) {
					return pushSettings();
				}
			}
			if (S.state) {
				R.updateDeviceStatus(S.state);
			}
		})
		.catch(function (err) {
			S.deviceLabels = {};
			var sel = document.getElementById("select-device");
			if (sel) {
				sel.innerHTML = "";
			}
			if (S.state) {
				R.updateDeviceStatus(S.state);
			}
			R.showFormBanner(err.message || "Could not list devices.");
		});
}
function libraryRootForSave() {
	var lib = document.getElementById("input-library-root");
	var path = lib ? lib.value.trim() : "";
	if (!path && S.state && S.state.library_root) {
		path = S.state.library_root;
	}
	if (!path && S.defaultLibraryRoot) {
		path = S.defaultLibraryRoot;
	}
	return path;
}
function pushSettings() {
	var sel = document.getElementById("select-device");
	var modeCopy = document.getElementById("chip-copy");
	var compressCheckbox = document.getElementById("easy-compress-checkbox");
	var deviceId = sel ? sel.value : "";
	var body = {
		library_root: libraryRootForSave(),
		ui_mode: S.uiMode,
		connection_method: R.selectedConnectionMethod(),
		transfer_mode: modeCopy?.classList.contains("selected") ? "copy" : "move",
		device_id: deviceId,
		device_label: S.deviceLabels[deviceId] || "",
		source_folders: R.selectedFolders(),
	};
	/* Only send when the control is enabled — avoid overwriting a stored
       preference while tools are unavailable (checkbox forced off). */
	if (compressCheckbox && !compressCheckbox.disabled) {
		body.compress_media = compressCheckbox.checked;
	}
	return R.api("PUT", "/api/settings", body)
		.then(function (data) {
			R.clearFormBanner();
			R.applyState(data);
			return data;
		})
		.catch(function (err) {
			R.showFormBanner(err.message || "Could not save settings.");
			throw err;
		});
}
R.updateExtractUi = updateExtractUi;
R.extractPhaseLabel = extractPhaseLabel;
R.extractIsActive = extractIsActive;
R.canStartConvert = canStartConvert;
R.updateExtractButtons = updateExtractButtons;
R.updateVisualizeUi = updateVisualizeUi;
R.updateConvertUi = updateConvertUi;
R.updateWarnings = updateWarnings;
R.loadDevices = loadDevices;
R.libraryRootForSave = libraryRootForSave;
R.pushSettings = pushSettings;

export {
	canStartConvert,
	extractIsActive,
	extractPhaseLabel,
	libraryRootForSave,
	loadDevices,
	pushSettings,
	updateConvertUi,
	updateExtractButtons,
	updateExtractUi,
	updateVisualizeUi,
	updateWarnings,
};
