import { apiSend } from "./api.ts";
import { errorMessage, onClick, showFormBanner } from "./dom.ts";
import { loadGallery } from "./gallery-timeline.ts";
import { applyState, showView } from "./shell.ts";
import { S } from "./state.ts";
import type { AppSnapshot, ManagedToolsStatus, ToolStatusRow } from "./types.ts";

function toolsBlockMainApp(next: AppSnapshot | null | undefined): boolean {
	return !!next?.tools_setup_pending;
}
function currentViewId(): string {
	const active = document.querySelector(".screen.active");
	return active ? active.id : "";
}
function toolDisplayName(toolId: string): string {
	const labels: Record<string, string> = {
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
function toolStatusText(tool: ToolStatusRow): string {
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
function fillToolStatusList(container: HTMLElement | null, tools: ToolStatusRow[] | undefined): void {
	if (!container || !tools) {
		return;
	}
	container.innerHTML = "";
	tools.forEach((tool) => {
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
		container.appendChild(row);
	});
}
function renderComponentsSetupHint(managedTools: ManagedToolsStatus | undefined): void {
	const el = document.getElementById("components-setup-hint");
	if (!el) {
		return;
	}
	const hint = managedTools?.setup_hint;
	if (!hint?.command) {
		el.hidden = true;
		el.textContent = "";
		return;
	}
	el.hidden = false;
	el.replaceChildren();
	if (hint.title) {
		const title = document.createElement("strong");
		title.textContent = hint.title;
		el.appendChild(title);
		el.appendChild(document.createElement("br"));
	}
	if (hint.detail) {
		const detail = document.createElement("span");
		detail.textContent = hint.detail + " ";
		el.appendChild(detail);
	}
	const code = document.createElement("code");
	code.textContent = hint.command;
	el.appendChild(code);
}
function renderComponentsList(managedTools: ManagedToolsStatus | undefined): void {
	if (!managedTools?.tools) {
		return;
	}
	fillToolStatusList(document.getElementById("components-tool-list"), managedTools.tools);
	fillToolStatusList(document.getElementById("settings-tool-list"), managedTools.tools);
	renderComponentsSetupHint(managedTools);
	const settingsDir = document.getElementById("settings-managed-tools-dir");
	if (settingsDir && managedTools.tools_dir) {
		settingsDir.textContent = managedTools.tools_dir;
	}
}
function shouldPromptComponentsSetup(next: AppSnapshot | null | undefined): boolean {
	if (!toolsBlockMainApp(next)) {
		sessionStorage.removeItem(S.COMPONENTS_DISMISS_KEY);
		return false;
	}
	if (sessionStorage.getItem(S.COMPONENTS_DISMISS_KEY) === "1") {
		return false;
	}
	return true;
}
function maybeShowComponentsScreen(next: AppSnapshot): void {
	if (!shouldPromptComponentsSetup(next)) {
		return;
	}
	const viewId = currentViewId();
	if (viewId === "view-settings" || viewId === "view-settings-tools" || viewId === "view-legal") {
		renderComponentsList(next.managed_tools);
		return;
	}
	renderComponentsList(next.managed_tools);
	showView("components", { skipHistory: true });
	const continueBtn = document.getElementById("btn-components-continue");
	if (continueBtn instanceof HTMLButtonElement) {
		continueBtn.disabled = false;
	}
}
function runComponentsEnsure(): Promise<ManagedToolsStatus> {
	return apiSend<ManagedToolsStatus>("POST", "/api/tools/ensure").then((payload) => {
		renderComponentsList(payload);
		return payload;
	});
}
function bindSettingsDesktop(): void {
	function showSettingsFeedback(message: string): void {
		const feedback = document.getElementById("settings-feedback");
		if (!feedback) {
			return;
		}
		feedback.textContent = message;
		feedback.classList.remove("panel-hidden");
	}
	function hideSettingsConfirms(): void {
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
		apiSend<AppSnapshot>("POST", "/api/preferences/clear")
			.then(applyState)
			.then(() => {
				hideSettingsConfirms();
				showSettingsFeedback("Preferences cleared.");
			})
			.catch((err: unknown) => {
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
		apiSend<AppSnapshot>("POST", "/api/library/reset")
			.then(applyState)
			.then(() => {
				hideSettingsConfirms();
				showSettingsFeedback("Library reset.");
				if (document.getElementById("view-gallery")?.classList.contains("active")) {
					loadGallery();
				}
			})
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Could not reset the library."));
			});
	});
	onClick("btn-settings-clear-cache", () => {
		apiSend("POST", "/api/browser-cache/clear")
			.then(() => {
				showSettingsFeedback("Browser cache cleared.");
			})
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Could not clear the browser cache."));
			});
	});
	onClick("btn-settings-tools", () => {
		if (S.state?.managed_tools) {
			renderComponentsList(S.state.managed_tools);
		}
		showView("settings-tools");
	});
	onClick("btn-settings-legal", () => {
		showView("legal");
	});
	onClick("btn-settings-tools-back", () => {
		showView("settings");
	});
	document.getElementById("btn-legal-back")?.addEventListener("click", () => {
		showView("settings");
	});
	onClick("btn-components-continue", () => {
		apiSend<ManagedToolsStatus>("POST", "/api/tools/components-continue")
			.then((payload) => {
				sessionStorage.setItem(S.COMPONENTS_DISMISS_KEY, "1");
				renderComponentsList(payload);
				return apiSend<AppSnapshot>("GET", "/api/settings");
			})
			.then(applyState)
			.then(() => {
				showView("home");
			})
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Could not continue setup."));
			});
	});
	onClick("btn-components-retry", () => {
		runComponentsEnsure().catch((err: unknown) => {
			showFormBanner(errorMessage(err, "Could not retry downloads."));
		});
	});
	onClick("btn-settings-delete-tools", () => {
		if (!window.confirm("Delete all downloaded components? System packages will not be removed.")) {
			return;
		}
		apiSend<ManagedToolsStatus>("DELETE", "/api/tools/downloaded")
			.then((payload) => {
				sessionStorage.removeItem(S.COMPONENTS_DISMISS_KEY);
				renderComponentsList(payload);
				return apiSend<AppSnapshot>("GET", "/api/settings");
			})
			.then(applyState)
			.then(() => {
				if (S.state && toolsBlockMainApp(S.state)) {
					showView("components", { skipHistory: true });
				}
			})
			.catch((err: unknown) => {
				showFormBanner(errorMessage(err, "Could not delete downloaded components."));
			});
	});
	onClick("btn-settings-retry-downloads", () => {
		runComponentsEnsure().catch((err: unknown) => {
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
	renderComponentsSetupHint,
	runComponentsEnsure,
	shouldPromptComponentsSetup,
	toolDisplayName,
	toolStatusText,
	toolsBlockMainApp,
};
