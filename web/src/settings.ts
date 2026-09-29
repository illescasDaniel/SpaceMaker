// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function toolsBlockMainApp(next) {
	return !!next?.tools_setup_pending;
}
function currentViewId() {
	var active = document.querySelector(".screen.active");
	return active ? active.id : "";
}
function toolDisplayName(toolId) {
	var labels = {
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
		return "Using system install (you chose Continue)";
	}
	if (tool.phase === "failed") {
		return tool.message || "Download failed";
	}
	return tool.message || "Not downloaded yet";
}
function fillToolStatusList(container, tools) {
	if (!container || !tools) {
		return;
	}
	container.innerHTML = "";
	tools.forEach(function (tool) {
		var row = document.createElement("div");
		row.className = "tool-row";
		var name = document.createElement("span");
		name.className = "tool-name";
		name.textContent = toolDisplayName(tool.tool_id);
		var status = document.createElement("span");
		status.className = "tool-status resolution-" + (tool.resolution || "missing");
		status.textContent = toolStatusText(tool);
		row.appendChild(name);
		row.appendChild(status);
		container.appendChild(row);
	});
}
function renderComponentsSetupHint(managedTools) {
	var el = document.getElementById("components-setup-hint");
	if (!el) {
		return;
	}
	var hint = managedTools?.setup_hint;
	var title;
	var detail;
	if (!hint?.command) {
		el.hidden = true;
		el.textContent = "";
		return;
	}
	el.hidden = false;
	el.replaceChildren();
	if (hint.title) {
		title = document.createElement("strong");
		title.textContent = hint.title;
		el.appendChild(title);
		el.appendChild(document.createElement("br"));
	}
	if (hint.detail) {
		detail = document.createElement("span");
		detail.textContent = hint.detail + " ";
		el.appendChild(detail);
	}
	var code = document.createElement("code");
	code.textContent = hint.command;
	el.appendChild(code);
}
function renderComponentsList(managedTools) {
	if (!managedTools?.tools) {
		return;
	}
	fillToolStatusList(document.getElementById("components-tool-list"), managedTools.tools);
	fillToolStatusList(document.getElementById("settings-tool-list"), managedTools.tools);
	renderComponentsSetupHint(managedTools);
	var settingsDir = document.getElementById("settings-managed-tools-dir");
	if (settingsDir && managedTools.tools_dir) {
		settingsDir.textContent = managedTools.tools_dir;
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
		return;
	}
	var viewId = currentViewId();
	if (viewId === "view-settings" || viewId === "view-settings-tools" || viewId === "view-legal") {
		renderComponentsList(next.managed_tools || {});
		return;
	}
	renderComponentsList(next.managed_tools || {});
	R.showView("components", { skipHistory: true });
	var continueBtn = document.getElementById("btn-components-continue");
	if (continueBtn) {
		continueBtn.disabled = false;
	}
}
function runComponentsEnsure() {
	return R.api("POST", "/api/tools/ensure").then(function (payload) {
		renderComponentsList(payload);
		return payload;
	});
}
function bindSettingsDesktop() {
	function showSettingsFeedback(message) {
		var feedback = document.getElementById("settings-feedback");
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
	R.onClick("btn-settings-clear-prefs", function () {
		hideSettingsConfirms();
		document.getElementById("settings-clear-prefs-confirm")?.classList.remove("panel-hidden");
	});
	R.onClick("btn-settings-clear-prefs-cancel", function () {
		document.getElementById("settings-clear-prefs-confirm")?.classList.add("panel-hidden");
	});
	R.onClick("btn-settings-clear-prefs-confirm", function () {
		R.api("POST", "/api/preferences/clear")
			.then(R.applyState)
			.then(function () {
				hideSettingsConfirms();
				showSettingsFeedback("Preferences cleared.");
			})
			.catch(function (err) {
				R.showFormBanner(err.message || "Could not clear preferences.");
			});
	});
	R.onClick("btn-settings-reset-gallery", function () {
		hideSettingsConfirms();
		document.getElementById("settings-reset-confirm")?.classList.remove("panel-hidden");
	});
	R.onClick("btn-settings-reset-cancel", function () {
		document.getElementById("settings-reset-confirm")?.classList.add("panel-hidden");
	});
	R.onClick("btn-settings-reset-confirm", function () {
		R.api("POST", "/api/library/reset")
			.then(R.applyState)
			.then(function () {
				hideSettingsConfirms();
				showSettingsFeedback("Library reset.");
				if (document.getElementById("view-gallery")?.classList.contains("active")) {
					R.loadGallery();
				}
			})
			.catch(function (err) {
				R.showFormBanner(err.message || "Could not reset the library.");
			});
	});
	R.onClick("btn-settings-clear-cache", function () {
		R.api("POST", "/api/browser-cache/clear")
			.then(function () {
				showSettingsFeedback("Browser cache cleared.");
			})
			.catch(function (err) {
				R.showFormBanner(err.message || "Could not clear the browser cache.");
			});
	});
	R.onClick("btn-settings-tools", function () {
		if (S.state?.managed_tools) {
			renderComponentsList(S.state.managed_tools);
		}
		R.showView("settings-tools");
	});
	R.onClick("btn-settings-legal", function () {
		R.showView("legal");
	});
	R.onClick("btn-settings-tools-back", function () {
		R.showView("settings");
	});
	document.getElementById("btn-legal-back").addEventListener("click", function () {
		R.showView("settings");
	});
	R.onClick("btn-components-continue", function () {
		R.api("POST", "/api/tools/components-continue")
			.then(function (payload) {
				sessionStorage.setItem(S.COMPONENTS_DISMISS_KEY, "1");
				renderComponentsList(payload);
				return R.api("GET", "/api/settings");
			})
			.then(R.applyState)
			.then(function () {
				R.showView("home");
				return null;
			})
			.catch(function (err) {
				R.showFormBanner(err.message || "Could not continue setup.");
			});
	});
	R.onClick("btn-components-retry", function () {
		runComponentsEnsure().catch(function (err) {
			R.showFormBanner(err.message || "Could not retry downloads.");
		});
	});
	R.onClick("btn-settings-delete-tools", function () {
		if (!window.confirm("Delete all downloaded components? System packages will not be removed.")) {
			return;
		}
		R.api("DELETE", "/api/tools/downloaded")
			.then(function (payload) {
				sessionStorage.removeItem(S.COMPONENTS_DISMISS_KEY);
				renderComponentsList(payload);
				return R.api("GET", "/api/settings");
			})
			.then(R.applyState)
			.then(function () {
				if (S.state && toolsBlockMainApp(S.state)) {
					R.showView("components", { skipHistory: true });
				}
			})
			.then(R.applyState)
			.catch(function (err) {
				R.showFormBanner(err.message || "Could not delete downloaded components.");
			});
	});
	R.onClick("btn-settings-retry-downloads", function () {
		runComponentsEnsure().catch(function (err) {
			R.showFormBanner(err.message || "Could not retry downloads.");
		});
	});
}
R.toolsBlockMainApp = toolsBlockMainApp;
R.currentViewId = currentViewId;
R.toolDisplayName = toolDisplayName;
R.toolStatusText = toolStatusText;
R.fillToolStatusList = fillToolStatusList;
R.renderComponentsSetupHint = renderComponentsSetupHint;
R.renderComponentsList = renderComponentsList;
R.shouldPromptComponentsSetup = shouldPromptComponentsSetup;
R.maybeShowComponentsScreen = maybeShowComponentsScreen;
R.runComponentsEnsure = runComponentsEnsure;
R.bindSettingsDesktop = bindSettingsDesktop;

export {
	bindSettingsDesktop,
	currentViewId,
	fillToolStatusList,
	maybeShowComponentsScreen,
	renderComponentsList,
	renderComponentsSetupHint,
	runComponentsEnsure,
	shouldPromptComponentsSetup,
	toolDisplayName,
	toolStatusText,
	toolsBlockMainApp,
};
