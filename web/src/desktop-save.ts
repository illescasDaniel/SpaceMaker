export interface DesktopSaveHandlers {
	onProgress: (percent: number, text: string) => void;
	onDone: (savedPath: string) => void;
	onError: (message: string) => void;
}

const SAVE_POLL_MS = 300;

function formatMegabytes(bytes: number): string {
	return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

/** True when the desktop shell can show a native Save dialog (a phone or plain browser has its own download UI). */
function canSaveOnDesktop(): boolean {
	return Boolean(window.pywebview?.api?.save_download);
}

/** The desktop webview has no download dialog: ask where to save via the native bridge, then report progress.
 * Resolves false when the dialog was cancelled (nothing started). */
async function saveOnDesktop(url: string, suggestedName: string, handlers: DesktopSaveHandlers): Promise<boolean> {
	const api = window.pywebview?.api;
	if (!api?.save_download) {
		return false;
	}
	const id = await Promise.resolve(api.save_download(new URL(url, window.location.origin).href, suggestedName));
	if (!id) {
		return false;
	}
	const tick = async (): Promise<void> => {
		const progress = await Promise.resolve(api.download_progress?.(id));
		if (!progress) {
			return;
		}
		if (!progress.done) {
			const sizes = progress.total
				? formatMegabytes(progress.downloaded) + " of " + formatMegabytes(progress.total)
				: "";
			handlers.onProgress(progress.percent, sizes);
			window.setTimeout(() => void tick(), SAVE_POLL_MS);
			return;
		}
		if (progress.error) {
			handlers.onError(progress.error);
		} else {
			handlers.onDone(progress.path);
		}
	};
	handlers.onProgress(0, "");
	await tick();
	return true;
}

export { canSaveOnDesktop, saveOnDesktop };
