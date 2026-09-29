import { apiSend } from "./api.ts";
import { bindDisclosure, errorMessage, onClick, showFormBanner } from "./dom.ts";
import { bindGalleryUi } from "./gallery.ts";
import { closeGalleryPhonePopup, toggleGalleryPhonePopup } from "./gallery-item.ts";
import { selectedConnectionMethod, syncConnectionButtons, validateStep1Form } from "./home.ts";
import { canStartConvert, extractIsActive, loadDevices, pushSettings, updateExtractButtons } from "./jobs.ts";
import { applyState, showView } from "./shell.ts";
import { S } from "./state.ts";
import type { AppSnapshot } from "./types.ts";

function bindHomeDesktop(): void {
	bindGalleryUi();
	document.getElementById("btn-lan-firewall-info")?.addEventListener("click", (ev) => {
		const panel = document.getElementById("lan-firewall-info-panel");
		if (!panel) {
			return;
		}
		const open = panel.classList.toggle("visible");
		panel.setAttribute("aria-hidden", open ? "false" : "true");
		if (ev.currentTarget instanceof HTMLElement) {
			ev.currentTarget.setAttribute("aria-expanded", open ? "true" : "false");
		}
	});
	document.getElementById("btn-connection-info")?.addEventListener("click", (ev) => {
		const panel = document.getElementById("connection-info-panel");
		if (!panel) {
			return;
		}
		const open = panel.classList.toggle("visible");
		panel.setAttribute("aria-hidden", open ? "false" : "true");
		if (ev.currentTarget instanceof HTMLElement) {
			ev.currentTarget.setAttribute("aria-expanded", open ? "true" : "false");
		}
	});
	bindDisclosure("btn-easy-qr-info", "easy-qr-info-panel");
	bindDisclosure("btn-easy-compress-info", "easy-compress-info-panel");
	bindDisclosure("btn-receive-qr-info", "receive-qr-info-panel");
	bindDisclosure("btn-send-qr-info", "send-qr-info-panel");
	bindDisclosure("btn-transfer-qr-info", "transfer-qr-info-panel");
	bindDisclosure("btn-wifi-qr-info", "wifi-qr-info-panel");
	const easyCompressCheckbox = document.getElementById("easy-compress-checkbox");
	if (easyCompressCheckbox instanceof HTMLInputElement) {
		easyCompressCheckbox.addEventListener("change", () => {
			if (easyCompressCheckbox.disabled) {
				return;
			}
			pushSettings();
		});
	}
	function switchConnectionMethod(method: string): Promise<unknown> {
		syncConnectionButtons(method);
		S.deviceLabels = {};
		const sel = document.getElementById("select-device");
		if (sel) {
			sel.innerHTML = "";
		}
		if (method === "wifi") {
			validateStep1Form(true);
			return pushSettings();
		}
		return loadDevices().then(() => pushSettings());
	}
	document.getElementById("btn-conn-wifi")?.addEventListener("click", () => {
		switchConnectionMethod("wifi");
	});
	document.getElementById("btn-conn-adb")?.addEventListener("click", () => {
		switchConnectionMethod("adb");
	});
	document.getElementById("btn-conn-afc")?.addEventListener("click", () => {
		switchConnectionMethod("afc");
	});
	const chipCopy = document.getElementById("chip-copy");
	const chipMove = document.getElementById("chip-move");
	chipCopy?.addEventListener("click", () => {
		if (selectedConnectionMethod() === "wifi") {
			return;
		}
		chipCopy.classList.add("selected");
		chipMove?.classList.remove("selected");
		pushSettings();
	});
	chipMove?.addEventListener("click", () => {
		if (chipMove instanceof HTMLButtonElement && chipMove.disabled) {
			return;
		}
		chipMove.classList.add("selected");
		chipCopy?.classList.remove("selected");
		pushSettings();
	});
	const libraryInput = document.getElementById("input-library-root");
	libraryInput?.addEventListener("input", () => {
		validateStep1Form(true);
		if (S.state) {
			updateExtractButtons(S.state);
		}
	});
	libraryInput?.addEventListener("change", () => {
		validateStep1Form(true);
		pushSettings();
	});
	document.getElementById("select-device")?.addEventListener("change", () => {
		validateStep1Form(true);
		pushSettings();
	});
	document.getElementById("btn-browse-library")?.addEventListener("click", () => {
		const lib = document.getElementById("input-library-root");
		const current = lib instanceof HTMLInputElement ? lib.value.trim() : "";
		if (window.pywebview?.api?.choose_library_folder) {
			Promise.resolve(window.pywebview.api.choose_library_folder(current))
				.then((path) => {
					if (path && lib instanceof HTMLInputElement) {
						lib.value = path;
						validateStep1Form(true);
						return pushSettings();
					}
					return null;
				})
				.catch(() => {
					showFormBanner("Could not open the folder picker.");
				});
			return;
		}
		showFormBanner("Browse works in the desktop app. Type an absolute path, or run uv run task spacemaker.");
		if (lib instanceof HTMLInputElement) {
			lib.focus();
		}
	});
	document.querySelectorAll("#folder-picker input").forEach((box) => {
		box.addEventListener("change", () => {
			pushSettings();
		});
	});
	document.getElementById("btn-start-extract")?.addEventListener("click", () => {
		if (!validateStep1Form(true).ok) {
			showFormBanner("Fix the highlighted fields before starting extract.");
			return;
		}
		const btnStart = document.getElementById("btn-start-extract");
		if (btnStart instanceof HTMLButtonElement) {
			btnStart.hidden = true;
			btnStart.disabled = true;
		}
		pushSettings()
			.then(() => apiSend<AppSnapshot>("POST", "/api/extract/start"))
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Extract could not start."));
				if (S.state) {
					updateExtractButtons(S.state);
				}
			});
	});
	document.getElementById("btn-pause-extract")?.addEventListener("click", () => {
		if (!S.state?.extract_controls?.pause) {
			return;
		}
		apiSend<AppSnapshot>("POST", "/api/extract/pause")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Pause failed."));
			});
	});
	document.getElementById("btn-resume-extract")?.addEventListener("click", () => {
		if (!S.state?.extract_controls?.resume) {
			return;
		}
		apiSend<AppSnapshot>("POST", "/api/extract/resume")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Resume failed."));
			});
	});
	document.getElementById("btn-stop-extract")?.addEventListener("click", () => {
		if (!S.state?.extract_controls?.stop) {
			return;
		}
		apiSend<AppSnapshot>("POST", "/api/extract/stop")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Stop failed."));
			});
	});
	document.getElementById("btn-stop-convert")?.addEventListener("click", () => {
		if (!S.state?.convert_controls?.stop) {
			return;
		}
		apiSend<AppSnapshot>("POST", "/api/convert/stop")
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Stop convert failed."));
			});
	});
	document.getElementById("btn-start-convert")?.addEventListener("click", () => {
		if (!canStartConvert(S.state || {})) {
			showFormBanner("Convert is not ready yet — check library path and originals/ folder.");
			return;
		}
		const sync = extractIsActive(S.state) ? Promise.resolve(S.state) : pushSettings();
		sync
			.then(() => apiSend<AppSnapshot>("POST", "/api/convert/start"))
			.then(applyState)
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Convert could not start."));
			});
	});
	document.getElementById("btn-move-errors")?.addEventListener("click", () => {
		apiSend("POST", "/api/error/move-to-processed")
			.then(() => apiSend<AppSnapshot>("GET", "/api/settings"))
			.then(applyState);
	});
	onClick("btn-open-gallery", () => {
		showView("gallery");
	});
	onClick("btn-easy-view-gallery", () => {
		showView("gallery");
	});
	onClick("btn-gallery-phone-help", (ev) => {
		ev.stopPropagation();
		toggleGalleryPhonePopup();
	});
	onClick("btn-gallery-phone-popup-close", () => {
		closeGalleryPhonePopup();
	});
	document.addEventListener("click", (ev) => {
		const popup = document.getElementById("gallery-phone-popup");
		const fab = document.getElementById("btn-gallery-phone-help");
		if (!popup || popup.classList.contains("panel-hidden")) {
			return;
		}
		if (
			(ev.target instanceof Node && popup.contains(ev.target)) ||
			(ev.target instanceof Node && fab?.contains(ev.target))
		) {
			return;
		}
		closeGalleryPhonePopup();
	});
}

export { bindHomeDesktop };
