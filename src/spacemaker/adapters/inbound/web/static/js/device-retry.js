/** Auto re-detection of an empty device list (specs/usb-file-transfer "Automatic re-detection"). */
/** Seconds between retries and how many retries follow the first (empty) listing. */
export const DEVICE_RETRY_INTERVAL_MS = 3000;
export const DEVICE_RETRY_MAX = 5;
/**
 * Start retrying after a first listing returned "empty". Never more than one listing in flight (the next
 * timer is armed only after the previous listing settles); at most `DEVICE_RETRY_MAX` retries; stops on
 * "found"/"error"/cancel. A listing that settles after `cancel()` is ignored.
 */
export function startDeviceRetry(options) {
	let cancelled = false;
	let timer;
	function schedule(attempt) {
		timer = setTimeout(() => {
			timer = undefined;
			if (cancelled) {
				return;
			}
			if (options.isActive && !options.isActive()) {
				cancelled = true;
				options.onGiveUp();
				return;
			}
			options.onSearching(attempt);
			options.list().then(
				(outcome) => {
					if (cancelled || outcome !== "empty") {
						return;
					}
					if (attempt >= DEVICE_RETRY_MAX) {
						options.onGiveUp();
						return;
					}
					schedule(attempt + 1);
				},
				() => undefined,
			);
		}, DEVICE_RETRY_INTERVAL_MS);
	}
	schedule(1);
	return {
		cancel: () => {
			cancelled = true;
			if (timer !== undefined) {
				clearTimeout(timer);
				timer = undefined;
			}
		},
	};
}
/** True while the screen with this id is the visible one (retries stop when the user leaves it). */
export function isScreenActive(viewId) {
	return document.getElementById(viewId)?.classList.contains("active") === true;
}
/** Shows "Searching for device…" in a module's device-status row (the row keeps its disconnected look). */
export function showDeviceSearching(rootId, textId) {
	const root = document.getElementById(rootId);
	const textEl = document.getElementById(textId);
	if (!root || !textEl) {
		return;
	}
	root.classList.remove("connected");
	root.classList.add("disconnected");
	textEl.textContent = "Searching for device…";
}
