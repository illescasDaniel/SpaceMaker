// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function bindHomeDesktop() {
	R.bindGalleryUi();
	document.getElementById("btn-lan-firewall-info").addEventListener("click", function () {
		var panel = document.getElementById("lan-firewall-info-panel");
		var open = panel.classList.toggle("visible");
		panel.setAttribute("aria-hidden", open ? "false" : "true");
		this.setAttribute("aria-expanded", open ? "true" : "false");
	});
	document.getElementById("btn-connection-info").addEventListener("click", function () {
		var panel = document.getElementById("connection-info-panel");
		var open = panel.classList.toggle("visible");
		panel.setAttribute("aria-hidden", open ? "false" : "true");
		this.setAttribute("aria-expanded", open ? "true" : "false");
	});
	R.bindInfoPanelToggle("btn-easy-qr-info", "easy-qr-info-panel");
	R.bindInfoPanelToggle("btn-easy-compress-info", "easy-compress-info-panel");
	R.bindInfoPanelToggle("btn-receive-qr-info", "receive-qr-info-panel");
	R.bindInfoPanelToggle("btn-send-qr-info", "send-qr-info-panel");
	R.bindInfoPanelToggle("btn-transfer-qr-info", "transfer-qr-info-panel");
	R.bindInfoPanelToggle("btn-wifi-qr-info", "wifi-qr-info-panel");
	var easyCompressCheckbox = document.getElementById("easy-compress-checkbox");
	if (easyCompressCheckbox) {
		easyCompressCheckbox.addEventListener("change", function () {
			if (easyCompressCheckbox.disabled) {
				return;
			}
			R.pushSettings();
		});
	}
	function switchConnectionMethod(method) {
		R.syncConnectionButtons(method);
		S.deviceLabels = {};
		var sel = document.getElementById("select-device");
		if (sel) {
			sel.innerHTML = "";
		}
		if (method === "wifi") {
			R.validateStep1Form(true);
			return R.pushSettings();
		}
		return R.loadDevices().then(function () {
			return R.pushSettings();
		});
	}
	document.getElementById("btn-conn-wifi").addEventListener("click", function () {
		switchConnectionMethod("wifi");
	});
	document.getElementById("btn-conn-adb").addEventListener("click", function () {
		switchConnectionMethod("adb");
	});
	document.getElementById("btn-conn-afc").addEventListener("click", function () {
		switchConnectionMethod("afc");
	});
	var chipCopy = document.getElementById("chip-copy");
	var chipMove = document.getElementById("chip-move");
	chipCopy.addEventListener("click", function () {
		if (R.selectedConnectionMethod() === "wifi") {
			return;
		}
		chipCopy.classList.add("selected");
		chipMove.classList.remove("selected");
		R.pushSettings();
	});
	chipMove.addEventListener("click", function () {
		if (chipMove.disabled) {
			return;
		}
		chipMove.classList.add("selected");
		chipCopy.classList.remove("selected");
		R.pushSettings();
	});
	var libraryInput = document.getElementById("input-library-root");
	libraryInput.addEventListener("input", function () {
		R.validateStep1Form(true);
		if (S.state) {
			R.updateExtractButtons(S.state);
		}
	});
	libraryInput.addEventListener("change", function () {
		R.validateStep1Form(true);
		R.pushSettings();
	});
	document.getElementById("select-device").addEventListener("change", function () {
		R.validateStep1Form(true);
		R.pushSettings();
	});
	document.getElementById("btn-browse-library").addEventListener("click", function () {
		var lib = document.getElementById("input-library-root");
		var current = lib ? lib.value.trim() : "";
		if (window.pywebview?.api?.choose_library_folder) {
			Promise.resolve(window.pywebview.api.choose_library_folder(current))
				.then(function (path) {
					if (path && lib) {
						lib.value = path;
						R.validateStep1Form(true);
						return R.pushSettings();
					}
					return null;
				})
				.catch(function () {
					R.showFormBanner("Could not open the folder picker.");
				});
			return;
		}
		R.showFormBanner("Browse works in the desktop app. Type an absolute path, or run uv run task spacemaker.");
		if (lib) {
			lib.focus();
		}
	});
	document.querySelectorAll("#folder-picker input").forEach(function (box) {
		box.addEventListener("change", R.pushSettings);
	});
	document.getElementById("btn-start-extract").addEventListener("click", function () {
		if (!R.validateStep1Form(true).ok) {
			R.showFormBanner("Fix the highlighted fields before starting extract.");
			return;
		}
		var btnStart = document.getElementById("btn-start-extract");
		if (btnStart) {
			btnStart.hidden = true;
			btnStart.disabled = true;
		}
		R.pushSettings()
			.then(function () {
				return R.api("POST", "/api/extract/start");
			})
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Extract could not start.");
				if (S.state) {
					R.updateExtractButtons(S.state);
				}
			});
	});
	document.getElementById("btn-pause-extract").addEventListener("click", function () {
		if (!S.state?.extract_controls?.pause) {
			return;
		}
		R.api("POST", "/api/extract/pause")
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Pause failed.");
			});
	});
	document.getElementById("btn-resume-extract").addEventListener("click", function () {
		if (!S.state?.extract_controls?.resume) {
			return;
		}
		R.api("POST", "/api/extract/resume")
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Resume failed.");
			});
	});
	document.getElementById("btn-stop-extract").addEventListener("click", function () {
		if (!S.state?.extract_controls?.stop) {
			return;
		}
		R.api("POST", "/api/extract/stop")
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Stop failed.");
			});
	});
	document.getElementById("btn-stop-convert").addEventListener("click", function () {
		if (!S.state?.convert_controls?.stop) {
			return;
		}
		R.api("POST", "/api/convert/stop")
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Stop convert failed.");
			});
	});
	document.getElementById("btn-start-convert").addEventListener("click", function () {
		if (!R.canStartConvert(S.state || {})) {
			R.showFormBanner("Convert is not ready yet — check library path and originals/ folder.");
			return;
		}
		var sync = R.extractIsActive(S.state || {}) ? Promise.resolve(S.state) : R.pushSettings();
		sync
			.then(function () {
				return R.api("POST", "/api/convert/start");
			})
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Convert could not start.");
			});
	});
	document.getElementById("btn-move-errors").addEventListener("click", function () {
		R.api("POST", "/api/error/move-to-processed")
			.then(function () {
				return R.api("GET", "/api/settings");
			})
			.then(R.applyState);
	});
	R.onClick("btn-open-gallery", function () {
		R.showView("gallery");
	});
	R.onClick("btn-easy-view-gallery", function () {
		R.showView("gallery");
	});
	R.onClick("btn-gallery-phone-help", function (ev) {
		ev.stopPropagation();
		R.toggleGalleryPhonePopup();
	});
	R.onClick("btn-gallery-phone-popup-close", function () {
		R.closeGalleryPhonePopup();
	});
	document.addEventListener("click", function (ev) {
		var popup = document.getElementById("gallery-phone-popup");
		var fab = document.getElementById("btn-gallery-phone-help");
		if (!popup || popup.classList.contains("panel-hidden")) {
			return;
		}
		if (popup.contains(ev.target) || fab?.contains(ev.target)) {
			return;
		}
		R.closeGalleryPhonePopup();
	});
}
R.bindHomeDesktop = bindHomeDesktop;

export { bindHomeDesktop };
