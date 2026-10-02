import { apiGet, apiSend } from "./api.ts";
import { bindDisclosure, errorMessage } from "./dom.ts";
import { loadServerInfo } from "./gallery-timeline.ts";
import { S } from "./state.ts";

interface PasscodeStatus {
	enabled: boolean;
	corrupt_warning: boolean;
}

const NOT_SET_TEXT = "Not set — anyone on your Wi-Fi can open the Gallery.";
const CORRUPT_TEXT = "The saved passcode could not be read and was cleared. Set a new one.";
const CHANGE_TEXT = "Enter a new passcode to replace the current one (Esc to cancel).";

let passcodeEnabled = false;

function dock(): HTMLElement | null {
	return document.getElementById("passcode-dock");
}

function input(): HTMLInputElement | null {
	const el = document.getElementById("passcode-input");
	return el instanceof HTMLInputElement ? el : null;
}

function setOpenStatus(text: string, isError = false): void {
	const el = document.getElementById("passcode-open-status");
	if (el) {
		el.textContent = text;
		el.classList.toggle("error", isError);
	}
}

function render(status: PasscodeStatus): void {
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
function refreshQrCodes(): void {
	for (const key of Object.keys(S.lastQrSrcByElementId)) {
		delete S.lastQrSrcByElementId[key];
	}
	loadServerInfo();
}

async function applyChange(send: () => Promise<PasscodeStatus>): Promise<void> {
	try {
		render(await send());
		refreshQrCodes();
	} catch (err) {
		setOpenStatus(errorMessage(err, "Could not save the passcode."), true);
	}
}

export function loadPasscodeStatus(): void {
	apiGet<PasscodeStatus>("/api/network-passcode")
		.then(render)
		.catch(() => undefined);
}

export function bindPasscodeDock(): void {
	bindDisclosure("btn-passcode-info", "passcode-info-panel");
	const submit = (): void => {
		const field = input();
		if (!field) {
			return;
		}
		void applyChange(() => apiSend<PasscodeStatus>("PUT", "/api/network-passcode", { passcode: field.value }));
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
		void applyChange(() => apiSend<PasscodeStatus>("DELETE", "/api/network-passcode"));
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
