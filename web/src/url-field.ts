/** Shared URL field: read-only input + Copy button (`.url-field` > `input`, `.url-copy`). */

const COPIED_MS = 1500;
const resetTimers = new WeakMap<HTMLElement, number>();

function legacyCopy(input: HTMLInputElement): boolean {
	input.select();
	try {
		return document.execCommand("copy");
	} catch {
		return false;
	}
}

/**
 * `execCommand("copy")` first: it needs no permission, whereas `navigator.clipboard` makes QtWebEngine
 * raise a permission request that pywebview's Qt backend answers with an invalid policy type (TypeError),
 * so the desktop app must not reach it unless the synchronous path failed.
 */
async function copyUrl(input: HTMLInputElement): Promise<boolean> {
	if (legacyCopy(input)) {
		return true;
	}
	if (navigator.clipboard && window.isSecureContext) {
		try {
			await navigator.clipboard.writeText(input.value);
			return true;
		} catch {
			return false;
		}
	}
	return false;
}

function copyButtonFor(input: HTMLElement): HTMLButtonElement | null {
	const button = input.closest(".url-field")?.querySelector(".url-copy");
	return button instanceof HTMLButtonElement ? button : null;
}

export function setUrlField(inputId: string, url: string): void {
	const input = document.getElementById(inputId);
	if (!(input instanceof HTMLInputElement)) {
		return;
	}
	input.value = url || "";
	const button = copyButtonFor(input);
	if (button) {
		button.disabled = !input.value;
	}
}

export function bindUrlFields(root: Document | HTMLElement = document): void {
	root.querySelectorAll<HTMLElement>(".url-field").forEach((field) => {
		const input = field.querySelector("input");
		const button = field.querySelector(".url-copy");
		const status = field.querySelector("[data-copy-status]");
		if (!input || !(button instanceof HTMLButtonElement)) {
			return;
		}
		input.addEventListener("focus", () => input.select());
		button.addEventListener("click", () => {
			void copyUrl(input).then((ok) => {
				if (!ok) {
					input.select();
					return;
				}
				button.classList.add("copied");
				if (status) {
					status.textContent = "Copied";
				}
				window.clearTimeout(resetTimers.get(button));
				resetTimers.set(
					button,
					window.setTimeout(() => {
						button.classList.remove("copied");
						if (status) {
							status.textContent = "";
						}
					}, COPIED_MS),
				);
			});
		});
	});
}
