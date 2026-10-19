import { apiSend } from "./api.ts";
import { openDevicePicker } from "./device-picker.ts";
import { errorMessage, showFormBanner } from "./dom.ts";
import { renderExtraSources } from "./extra-sources.ts";
import { selectedConnectionMethod } from "./home.ts";
import { applyState } from "./shell.ts";
import { S } from "./state.ts";
import type { AppSnapshot } from "./types.ts";

/** Photo-backup Step 1 extras (folders/files beyond the presets), kept on the server session. */
function saveWizardExtras(paths: string[]): Promise<void> {
	return apiSend<AppSnapshot>("POST", "/api/extract/extras", { paths })
		.then(applyState)
		.catch((err: unknown) => {
			showFormBanner(errorMessage(err, "Could not save the added items."));
		});
}

function currentWizardExtras(): string[] {
	return S.state?.extract_extra_paths ?? [];
}

function syncWizardExtras(next: AppSnapshot): void {
	renderExtraSources("wz-extra-sources", next.extract_extra_paths, (remaining) => {
		void saveWizardExtras(remaining);
	});
}

function openWizardPicker(kind: "files" | "folders"): void {
	const method = selectedConnectionMethod();
	const sel = document.getElementById("select-device");
	const deviceId = sel instanceof HTMLSelectElement ? sel.value : "";
	if (method === "wifi" || !deviceId) {
		showFormBanner("Add folder/files needs a connected, authorized device.");
		return;
	}
	openDevicePicker({
		origin: "wizard",
		originLabel: "USB photo backup",
		method: method === "afc" ? "afc" : "adb",
		deviceId,
		deviceLabel: S.deviceLabels[deviceId] || "",
		kind,
		mediaOnly: true,
		onAdd: (items) => {
			void saveWizardExtras(currentWizardExtras().concat(items.map((item) => item.path)));
		},
	});
}

function bindWizardExtras(): void {
	document.getElementById("btn-wz-add-folder")?.addEventListener("click", () => {
		openWizardPicker("folders");
	});
	document.getElementById("btn-wz-add-files")?.addEventListener("click", () => {
		openWizardPicker("files");
	});
}

export { bindWizardExtras, syncWizardExtras };
