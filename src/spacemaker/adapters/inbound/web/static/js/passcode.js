import { apiGet, apiSend } from "./api.js";
import { errorMessage } from "./dom.js";
import { loadServerInfo } from "./gallery-timeline.js";
import { S } from "./state.js";

const NOT_SET_TEXT = "Not set — anyone on your Wi-Fi can open the Gallery.";
const CORRUPT_TEXT = "The saved passcode could not be read and was cleared. Set a new one.";
const CHANGE_TEXT = "Enter a new passcode to replace the current one (Esc to cancel).";
let passcodeEnabled = false;
function dock() {
	return document.getElementById("passcode-dock");
}
function input() {
	const el = document.getElementById("passcode-input");
	return el instanceof HTMLInputElement ? el : null;
}
function setOpenStatus(text, isError = false) {
	const el = document.getElementById("passcode-open-status");
	if (el) {
		el.textContent = text;
		el.classList.toggle("error", isError);
	}
}
function render(status) {
	const el = dock();
	if (!el) {
		return;
	}
	passcodeEnabled = status.enabled;
	el.dataset.state = status.enabled ? "active" : "open";
	const field = input();
	if (field) {
		field.value = "";
		field.placeholder = "Choose a passcode";
	}
	setOpenStatus(status.corrupt_warning ? CORRUPT_TEXT : NOT_SET_TEXT, status.corrupt_warning);
}
/** Phone QR images encode the sign-in token, so they must be re-fetched after any change. */
function refreshQrCodes() {
	for (const key of Object.keys(S.lastQrSrcByElementId)) {
		delete S.lastQrSrcByElementId[key];
	}
	loadServerInfo();
}
async function applyChange(send) {
	try {
		render(await send());
		refreshQrCodes();
	} catch (err) {
		setOpenStatus(errorMessage(err, "Could not save the passcode."), true);
	}
}
export function loadPasscodeStatus() {
	apiGet("/api/network-passcode")
		.then(render)
		.catch(() => undefined);
}
/** The dock's info panel is shown by the shared `.info-panel.visible` CSS, not the `hidden` attribute. */
function bindInfoPanel() {
	const button = document.getElementById("btn-passcode-info");
	const panel = document.getElementById("passcode-info-panel");
	button?.addEventListener("click", () => {
		if (!panel) {
			return;
		}
		const open = panel.classList.toggle("visible");
		panel.setAttribute("aria-hidden", open ? "false" : "true");
		button.setAttribute("aria-expanded", open ? "true" : "false");
	});
}
export function bindPasscodeDock() {
	bindInfoPanel();
	const submit = () => {
		const field = input();
		if (!field) {
			return;
		}
		void applyChange(() => apiSend("PUT", "/api/network-passcode", { passcode: field.value }));
	};
	document.getElementById("btn-passcode-set")?.addEventListener("click", submit);
	input()?.addEventListener("keydown", (ev) => {
		if (ev.key === "Enter") {
			submit();
		} else if (ev.key === "Escape" && dock()?.dataset.state === "open" && passcodeEnabled) {
			loadPasscodeStatus();
		}
	});
	document.getElementById("btn-passcode-clear")?.addEventListener("click", () => {
		void applyChange(() => apiSend("DELETE", "/api/network-passcode"));
	});
	document.getElementById("btn-passcode-change")?.addEventListener("click", () => {
		const el = dock();
		const field = input();
		if (!el || !field) {
			return;
		}
		el.dataset.state = "open";
		field.value = "";
		field.placeholder = "New passcode";
		setOpenStatus(CHANGE_TEXT);
		field.focus();
	});
	loadPasscodeStatus();
}
