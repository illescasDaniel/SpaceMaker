import { apiSend } from "./api.js";
import { openDevicePicker } from "./device-picker.js";
import { errorMessage, showFormBanner } from "./dom.js";
import { renderExtraSources } from "./extra-sources.js";
import { selectedConnectionMethod } from "./home.js";
import { applyState } from "./shell.js";
import { S } from "./state.js";

/** Photo-backup Step 1 extras (folders/files beyond the presets), kept on the server session. */
function saveWizardExtras(paths) {
	return apiSend("POST", "/api/extract/extras", { paths })
		.then(applyState)
		.catch((err) => {
			showFormBanner(errorMessage(err, "Could not save the added items."));
		});
}
function currentWizardExtras() {
	return S.state?.extract_extra_paths ?? [];
}
function syncWizardExtras(next) {
	renderExtraSources("wz-extra-sources", next.extract_extra_paths, (remaining) => {
		void saveWizardExtras(remaining);
	});
}
function openWizardPicker() {
	const method = selectedConnectionMethod();
	const sel = document.getElementById("select-device");
	const deviceId = sel instanceof HTMLSelectElement ? sel.value : "";
	if (method === "wifi" || !deviceId) {
		showFormBanner("Add more needs a connected, authorized device.");
		return;
	}
	openDevicePicker({
		origin: "wizard",
		originLabel: "USB photo backup",
		method: method === "afc" ? "afc" : "adb",
		deviceId,
		deviceLabel: S.deviceLabels[deviceId] || "",
		kind: "both",
		mediaOnly: true,
		onAdd: (items) => {
			void saveWizardExtras(currentWizardExtras().concat(items.map((item) => item.path)));
		},
	});
}
function bindWizardExtras() {
	document.getElementById("btn-wz-add-more")?.addEventListener("click", openWizardPicker);
}

export { bindWizardExtras, syncWizardExtras };
