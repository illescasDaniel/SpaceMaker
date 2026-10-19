/** Auto re-detection of an empty device list (specs/usb-file-transfer "Automatic re-detection"). */

/** Seconds between retries and how many retries follow the first (empty) listing. */
export const DEVICE_RETRY_INTERVAL_MS = 3000;
export const DEVICE_RETRY_MAX = 5;

/** What one device-list attempt produced; `error` attempts end the retry run. */
export type DeviceListOutcome = "found" | "empty" | "error";

export interface DeviceRetryOptions {
	/** Runs one listing (the module's own refresh) and reports its outcome. */
	list: () => Promise<DeviceListOutcome>;
	/** Called before each scheduled retry with the 1-based attempt number (drives "Searching for device…"). */
	onSearching: (attempt: number) => void;
	/** Checked before each retry; once false the run stops and `onGiveUp` restores the normal status (view left, method changed, job started). */
	isActive?: () => boolean;
	/** Called when retries run out, or the run becomes inactive, to restore "No device found". */
	onGiveUp: () => void;
}

/** Handle for one retry run; `cancel()` is idempotent and also called on method switch, view change or Start. */
export interface DeviceRetryRun {
	cancel: () => void;
}

/**
 * Start retrying after a first listing returned "empty". Never more than one listing in flight (the next
 * timer is armed only after the previous listing settles); at most `DEVICE_RETRY_MAX` retries; stops on
 * "found"/"error"/cancel. A listing that settles after `cancel()` is ignored.
 */
export function startDeviceRetry(options: DeviceRetryOptions): DeviceRetryRun {
	let cancelled = false;
	let timer: ReturnType<typeof setTimeout> | undefined;

	function schedule(attempt: number): void {
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
export function isScreenActive(viewId: string): boolean {
	return document.getElementById(viewId)?.classList.contains("active") === true;
}

/** Shows "Searching for device…" in a module's device-status row (the row keeps its disconnected look). */
export function showDeviceSearching(rootId: string, textId: string): void {
	const root = document.getElementById(rootId);
	const textEl = document.getElementById(textId);
	if (!root || !textEl) {
		return;
	}
	root.classList.remove("connected");
	root.classList.add("disconnected");
	textEl.textContent = "Searching for device…";
}
