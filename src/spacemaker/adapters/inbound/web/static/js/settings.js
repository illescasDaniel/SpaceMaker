import { apiGet, apiSend } from "./api.js";
import { COMPONENTS_POLL_MS, detailsExpandedForSummary, shouldRunComponentsPoll } from "./components-setup.js";
import { copyTextToClipboard, errorMessage, onClick, showFormBanner } from "./dom.js";
import { loadGallery } from "./gallery-timeline.js";
import { applyState, showView } from "./shell.js";
import { S } from "./state.js";

let componentsPollTimer = null;
let componentsPollInFlight = false;
function toolsBlockMainApp(next) {
	return !!next?.tools_setup_pending;
}
function currentViewId() {
	const active = document.querySelector(".screen.active");
	return active ? active.id : "";
}
function toolDisplayName(toolId) {
	const labels = {
		adb: "adb",
		ffmpeg: "ffmpeg / ffprobe",
		ffprobe: "ffprobe",
		magick: "magick (ImageMagick)",
		avifenc: "avifenc (libavif)",
		exiftool: "exiftool",
		idevice_id: "idevice_id (libimobiledevice)",
		idevicepair: "idevicepair (libimobiledevice)",
		ideviceinfo: "ideviceinfo (libimobiledevice)",
		ifuse: "ifuse (libimobiledevice)",
	};
	return labels[toolId] || toolId;
}
function toolStatusText(tool) {
	if (tool.phase === "downloading" || tool.message === "Waiting for download") {
		return tool.phase === "downloading" ? "Downloading…" : "Waiting for download…";
	}
	if (tool.resolution === "managed") {
		return "Ready (downloaded)";
	}
	if (tool.resolution === "path") {
		return "Using system install";
	}
	if (tool.phase === "failed") {
		return tool.message || "Download failed";
	}
	return tool.message || "Not downloaded yet";
}
function bindCopyButton(btn, getCommand) {
	if (!(btn instanceof HTMLButtonElement)) {
		return;
	}
	btn.addEventListener("click", () => {
		const command = getCommand();
		if (!command) {
			return;
		}
		void copyTextToClipboard(command).then((ok) => {
			btn.textContent = ok ? "Copied" : "Copy failed";
			window.setTimeout(() => {
				btn.textContent = "Copy";
			}, 1500);
		});
	});
}
function fillToolStatusList(container, tools) {
	if (!container || !tools) {
		return;
	}
	container.innerHTML = "";
	tools.forEach((tool) => {
		const block = document.createElement("div");
		block.className = "tool-block";
		const row = document.createElement("div");
		row.className = "tool-row";
		const name = document.createElement("span");
		name.className = "tool-name";
		name.textContent = toolDisplayName(tool.tool_id);
		const status = document.createElement("span");
		status.className = "tool-status resolution-" + (tool.resolution || "missing");
		status.textContent = toolStatusText(tool);
		row.appendChild(name);
		row.appendChild(status);
		block.appendChild(row);
		if (tool.install_command) {
			const hint = document.createElement("div");
			hint.className = "tool-install-hint";
			const label = document.createElement("span");
			label.className = "tool-install-hint-label";
			label.textContent = "Install:";
			const cmdRow = document.createElement("div");
			cmdRow.className = "tool-install-cmd-row";
			const code = document.createElement("code");
			code.textContent = tool.install_command;
			const copyBtn = document.createElement("button");
			copyBtn.type = "button";
			copyBtn.className = "btn btn-secondary tool-install-copy";
			copyBtn.textContent = "Copy";
			copyBtn.setAttribute("aria-label", `Copy install command for ${toolDisplayName(tool.tool_id)}`);
			const command = tool.install_command;
			copyBtn.addEventListener("click", () => {
				void copyTextToClipboard(command).then((ok) => {
					copyBtn.textContent = ok ? "Copied" : "Copy failed";
					window.setTimeout(() => {
						copyBtn.textContent = "Copy";
					}, 1500);
				});
			});
			cmdRow.appendChild(code);
			cmdRow.appendChild(copyBtn);
			hint.appendChild(label);
			hint.appendChild(cmdRow);
			block.appendChild(hint);
		}
		container.appendChild(block);
	});
}
function renderIphoneUsbHint(managedTools) {
	const el = document.getElementById("components-iphone-packages");
	if (!el) {
		return;
	}
	el.hidden = !managedTools?.show_iphone_usb_hint;
}
function renderComponentsSteppedChrome(managedTools) {
	const pmStep = document.getElementById("components-pm-step");
	const pmCommand = document.getElementById("components-pm-command");
	const bulkStep = document.getElementById("components-bulk-step");
	const bulkTitle = document.getElementById("components-bulk-step-title");
	const bulkCommand = document.getElementById("components-bulk-command");
	const chip = document.getElementById("components-status-chip");
	const summary = document.getElementById("components-status-summary");
	const details = document.getElementById("components-details");
	const pmCmd = managedTools.package_manager_command || "";
	if (pmStep) {
		pmStep.hidden = !pmCmd;
	}
	if (pmCommand && pmCmd) {
		pmCommand.textContent = pmCmd;
	}
	const bulkCmd = managedTools.install_all_command || "";
	if (bulkStep) {
		bulkStep.hidden = !bulkCmd;
	}
	if (bulkTitle) {
		bulkTitle.textContent = pmCmd ? "2. Install missing tools" : "1. Install missing tools";
	}
	if (bulkCommand && bulkCmd) {
		bulkCommand.textContent = bulkCmd;
	}
	const status = managedTools.summary_status || "missing";
	if (chip) {
		chip.className = "components-status-chip " + status;
		chip.textContent = status === "ok" ? "OK" : status === "warning" ? "Warning" : "Missing";
	}
	if (summary) {
		summary.textContent = managedTools.summary_line || "";
	}
	if (details instanceof HTMLDetailsElement) {
		details.open = managedTools.details_expanded ?? detailsExpandedForSummary(status);
	}
}
function renderComponentsList(managedTools) {
	if (!managedTools?.tools) {
		return;
	}
	fillToolStatusList(document.getElementById("components-tool-list"), managedTools.tools);
	fillToolStatusList(document.getElementById("settings-tool-list"), managedTools.tools);
	renderIphoneUsbHint(managedTools);
	renderComponentsSteppedChrome(managedTools);
	const settingsDir = document.getElementById("settings-managed-tools-dir");
	if (settingsDir && managedTools.tools_dir) {
		settingsDir.textContent = managedTools.tools_dir;
	}
}
function stopComponentsPoll() {
	if (componentsPollTimer !== null) {
		clearInterval(componentsPollTimer);
		componentsPollTimer = null;
	}
}
function pollComponentsStatusOnce() {
	if (currentViewId() !== "view-components" || componentsPollInFlight) {
		return;
	}
	componentsPollInFlight = true;
	apiGet("/api/tools/status")
		.then((payload) => {
			renderComponentsList(payload);
			if (S.state) {
				S.state.managed_tools = payload;
				S.state.tools_setup_pending = payload.setup_pending;
			}
		})
		.catch(() => {
			/* keep last good snapshot */
		})
		.finally(() => {
			componentsPollInFlight = false;
		});
}
function startComponentsPoll() {
	stopComponentsPoll();
	componentsPollTimer = setInterval(pollComponentsStatusOnce, COMPONENTS_POLL_MS);
}
function syncComponentsPollForView() {
	if (shouldRunComponentsPoll(currentViewId())) {
		startComponentsPoll();
	} else {
		stopComponentsPoll();
	}
}
function shouldPromptComponentsSetup(next) {
	if (!toolsBlockMainApp(next)) {
		sessionStorage.removeItem(S.COMPONENTS_DISMISS_KEY);
		return false;
	}
	if (sessionStorage.getItem(S.COMPONENTS_DISMISS_KEY) === "1") {
		return false;
	}
	return true;
}
function maybeShowComponentsScreen(next) {
	if (!shouldPromptComponentsSetup(next)) {
		syncComponentsPollForView();
		return;
	}
	const viewId = currentViewId();
	if (viewId === "view-settings" || viewId === "view-settings-tools" || viewId === "view-legal") {
		renderComponentsList(next.managed_tools);
		syncComponentsPollForView();
		return;
	}
	renderComponentsList(next.managed_tools);
	showView("components", { skipHistory: true });
	const continueBtn = document.getElementById("btn-components-continue");
	if (continueBtn instanceof HTMLButtonElement) {
		continueBtn.disabled = false;
	}
	startComponentsPoll();
}
function runComponentsEnsure() {
	return apiSend("POST", "/api/tools/ensure").then((payload) => {
		renderComponentsList(payload);
		return payload;
	});
}
function bindSettingsDesktop() {
	bindCopyButton(document.getElementById("btn-components-pm-copy"), () => {
		return document.getElementById("components-pm-command")?.textContent || "";
	});
	bindCopyButton(document.getElementById("btn-components-bulk-copy"), () => {
		return document.getElementById("components-bulk-command")?.textContent || "";
	});
	function showSettingsFeedback(message) {
		const feedback = document.getElementById("settings-feedback");
		if (!feedback) {
			return;
		}
		feedback.textContent = message;
		feedback.classList.remove("panel-hidden");
	}
	function hideSettingsConfirms() {
		document.getElementById("settings-clear-prefs-confirm")?.classList.add("panel-hidden");
		document.getElementById("settings-reset-confirm")?.classList.add("panel-hidden");
	}
	onClick("btn-settings-clear-prefs", () => {
		hideSettingsConfirms();
		document.getElementById("settings-clear-prefs-confirm")?.classList.remove("panel-hidden");
	});
	onClick("btn-settings-clear-prefs-cancel", () => {
		document.getElementById("settings-clear-prefs-confirm")?.classList.add("panel-hidden");
	});
	onClick("btn-settings-clear-prefs-confirm", () => {
		apiSend("POST", "/api/preferences/clear")
			.then(applyState)
			.then(() => {
				hideSettingsConfirms();
				showSettingsFeedback("Preferences cleared.");
			})
			.catch((err) => {
				showFormBanner(errorMessage(err, "Could not clear preferences."));
			});
	});
	onClick("btn-settings-reset-gallery", () => {
		hideSettingsConfirms();
		document.getElementById("settings-reset-confirm")?.classList.remove("panel-hidden");
	});
	onClick("btn-settings-reset-cancel", () => {
		document.getElementById("settings-reset-confirm")?.classList.add("panel-hidden");
	});
	onClick("btn-settings-reset-confirm", () => {
		apiSend("POST", "/api/library/reset")
			.then(applyState)
			.then(() => {
				hideSettingsConfirms();
				showSettingsFeedback("Library reset.");
				if (document.getElementById("view-gallery")?.classList.contains("active")) {
					loadGallery();
				}
			})
			.catch((err) => {
				showFormBanner(errorMessage(err, "Could not reset the library."));
			});
	});
	onClick("btn-settings-clear-cache", () => {
		apiSend("POST", "/api/browser-cache/clear")
			.then(() => {
				showSettingsFeedback("Browser cache cleared.");
			})
			.catch((err) => {
				showFormBanner(errorMessage(err, "Could not clear the browser cache."));
			});
	});
	onClick("btn-settings-tools", () => {
		if (S.state?.managed_tools) {
			renderComponentsList(S.state.managed_tools);
		}
		showView("settings-tools");
		stopComponentsPoll();
	});
	onClick("btn-settings-legal", () => {
		showView("legal");
		stopComponentsPoll();
	});
	onClick("btn-settings-tools-back", () => {
		showView("settings");
		stopComponentsPoll();
	});
	document.getElementById("btn-legal-back")?.addEventListener("click", () => {
		showView("settings");
		stopComponentsPoll();
	});
	onClick("btn-components-continue", () => {
		stopComponentsPoll();
		apiSend("POST", "/api/tools/components-continue")
			.then((payload) => {
				sessionStorage.setItem(S.COMPONENTS_DISMISS_KEY, "1");
				renderComponentsList(payload);
				return apiSend("GET", "/api/settings");
			})
			.then(applyState)
			.then(() => {
				showView("home");
			})
			.catch((err) => {
				showFormBanner(errorMessage(err, "Could not continue setup."));
				syncComponentsPollForView();
			});
	});
	onClick("btn-components-retry", () => {
		runComponentsEnsure().catch((err) => {
			showFormBanner(errorMessage(err, "Could not retry downloads."));
		});
	});
	onClick("btn-settings-delete-tools", () => {
		if (!window.confirm("Delete all downloaded components? System packages will not be removed.")) {
			return;
		}
		apiSend("DELETE", "/api/tools/downloaded")
			.then((payload) => {
				sessionStorage.removeItem(S.COMPONENTS_DISMISS_KEY);
				renderComponentsList(payload);
				return apiSend("GET", "/api/settings");
			})
			.then(applyState)
			.then(() => {
				if (S.state && toolsBlockMainApp(S.state)) {
					showView("components", { skipHistory: true });
					startComponentsPoll();
				}
			})
			.catch((err) => {
				showFormBanner(errorMessage(err, "Could not delete downloaded components."));
			});
	});
	onClick("btn-settings-retry-downloads", () => {
		runComponentsEnsure().catch((err) => {
			showFormBanner(errorMessage(err, "Could not retry downloads."));
		});
	});
}

export {
	bindSettingsDesktop,
	currentViewId,
	fillToolStatusList,
	maybeShowComponentsScreen,
	renderComponentsList,
	renderIphoneUsbHint,
	runComponentsEnsure,
	shouldPromptComponentsSetup,
	startComponentsPoll,
	stopComponentsPoll,
	syncComponentsPollForView,
	toolDisplayName,
	toolStatusText,
	toolsBlockMainApp,
};
