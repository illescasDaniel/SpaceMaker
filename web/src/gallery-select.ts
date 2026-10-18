import { ApiError, apiGet, apiSend } from "./api.ts";
import { canSaveOnDesktop, saveOnDesktop } from "./desktop-save.ts";
import { errorMessage, onClick } from "./dom.ts";
import { triggerFileDownload } from "./gallery-item.ts";
import {
	batchActionsEnabled,
	deselect,
	isOverLimit,
	isSelected,
	isSelecting,
	MAX_GALLERY_BATCH_ITEMS,
	onSelectionChange,
	selectedCount,
	selectedPaths,
	setSelecting,
} from "./gallery-selection.ts";
import { removeGalleryItem } from "./gallery-timeline.ts";
import type { BatchConvertItemResult, BatchTrashResponse, GalleryBatchConvertJob } from "./types.ts";

const BATCH_POLL_MS = 700;
const DOWNLOAD_NOTE = "Files are zipped exactly as stored. Nothing is converted.";
const CONVERT_NOTE = "Photos → JPEG, videos → MP4. Your originals are not changed.";

function el(id: string): HTMLElement | null {
	return document.getElementById(id);
}
function setPanelVisible(id: string, visible: boolean): void {
	el(id)?.classList.toggle("panel-hidden", !visible);
}
function itemsLabel(count: number): string {
	return String(count) + (count === 1 ? " item" : " items");
}

/** Sync the select-mode chrome (toolbar button, bar, tile classes) to the selection state. */
function refreshSelectionUi(): void {
	const selecting = isSelecting();
	const count = selectedCount();
	el("gallery-layout")?.classList.toggle("is-selecting", selecting);
	const toggle = el("btn-gallery-select");
	if (toggle) {
		toggle.textContent = selecting ? "Done" : "Select";
		toggle.setAttribute("aria-pressed", String(selecting));
	}
	const bar = el("gallery-selection-bar");
	if (bar) {
		bar.hidden = !selecting;
	}
	const countEl = el("gallery-selection-count");
	if (countEl) {
		countEl.textContent = isOverLimit()
			? String(count) + " selected · max " + String(MAX_GALLERY_BATCH_ITEMS)
			: String(count) + " selected";
	}
	const enabled = batchActionsEnabled();
	for (const id of ["btn-gallery-batch-download", "btn-gallery-batch-convert", "btn-gallery-batch-trash"]) {
		const button = el(id) as HTMLButtonElement | null;
		if (button) {
			button.disabled = !enabled;
		}
	}
	if (count === 0) {
		setPanelVisible("gallery-trash-confirm", false);
		setPanelVisible("gallery-cpu-confirm", false);
	}
	document.querySelectorAll<HTMLElement>(".thumb[data-path]").forEach((tile) => {
		const on = isSelected(tile.dataset.path ?? "");
		tile.classList.toggle("selected", on);
		if (selecting) {
			tile.setAttribute("aria-pressed", String(on));
		} else {
			tile.removeAttribute("aria-pressed");
		}
	});
}

interface BatchAlertView {
	title: string;
	detail?: string;
	percent: number | null;
	lines?: string[];
	canDownload?: boolean;
}
function showBatchAlert(view: BatchAlertView): void {
	const alertEl = el("gallery-batch-alert");
	if (!alertEl) {
		return;
	}
	alertEl.hidden = false;
	const title = el("gallery-batch-alert-title");
	if (title) {
		title.textContent = view.title;
	}
	const detail = el("gallery-batch-alert-detail");
	if (detail) {
		detail.textContent = view.detail ?? "";
		detail.hidden = !view.detail;
	}
	const progress = el("gallery-batch-progress");
	if (progress) {
		progress.hidden = view.percent === null;
		progress.setAttribute("aria-valuenow", String(view.percent ?? 0));
	}
	const fill = el("gallery-batch-progress-fill");
	if (fill) {
		fill.style.width = String(view.percent ?? 0) + "%";
	}
	const list = el("gallery-batch-alert-list");
	if (list) {
		list.textContent = "";
		for (const line of view.lines ?? []) {
			const li = document.createElement("li");
			li.textContent = line;
			list.appendChild(li);
		}
		list.hidden = !view.lines?.length;
	}
	const actions = el("gallery-batch-alert-actions");
	if (actions) {
		actions.hidden = view.percent !== null;
	}
	const zip = el("btn-gallery-batch-zip") as HTMLButtonElement | null;
	if (zip) {
		zip.hidden = !view.canDownload;
		zip.disabled = false;
	}
}
function hideBatchAlert(): void {
	batchPollToken += 1;
	const alertEl = el("gallery-batch-alert");
	if (alertEl) {
		alertEl.hidden = true;
	}
}

async function runTrash(): Promise<void> {
	const paths = selectedPaths();
	setPanelVisible("gallery-trash-confirm", false);
	if (!paths.length) {
		return;
	}
	try {
		const response = await apiSend<BatchTrashResponse>("POST", "/api/gallery/batch/trash", { relative_paths: paths });
		const done = response.results.filter((r) => r.outcome !== "failed").map((r) => r.relative_path);
		const failed = response.results.filter((r) => r.outcome === "failed");
		deselect(done);
		for (const path of done) {
			// The timeline animates the tile out in place; a calendar day grid has no such helper.
			removeGalleryItem(path);
			document.querySelectorAll<HTMLElement>("#calendar-day-thumbs .thumb[data-path]").forEach((tile) => {
				if (tile.dataset.path === path) {
					tile.remove();
				}
			});
		}
		if (failed.length) {
			showBatchAlert({
				title: String(done.length) + " moved to Trash · " + String(failed.length) + " could not be moved",
				detail: "The ones that failed are still in your Gallery and stay selected.",
				percent: null,
				lines: failed.map((r) => r.relative_path + " — " + (r.reason || "could not move to Trash")),
			});
		}
	} catch (err) {
		showBatchAlert({
			title: "Could not move to Trash",
			detail: errorMessage(err, "Something went wrong. Nothing was changed."),
			percent: null,
		});
	}
}

let batchPollToken = 0;

function skippedLines(results: BatchConvertItemResult[]): string[] {
	return results
		.filter((r) => r.outcome === "skipped")
		.map((r) => r.relative_path + " — " + (r.reason || "could not convert"));
}
function showConvertRunning(job: GalleryBatchConvertJob): void {
	const download = job.kind === "download";
	showBatchAlert({
		title:
			(download ? "Preparing " : "Converting ") +
			String(Math.max(job.current_index, 1)) +
			" of " +
			String(job.item_count) +
			"…",
		detail: download ? DOWNLOAD_NOTE : CONVERT_NOTE,
		percent: job.percent || 0,
	});
}
function showConvertFinished(job: GalleryBatchConvertJob): void {
	const download = job.kind === "download";
	const verb = download ? "ready" : "converted";
	const converted = job.results.filter((r) => r.outcome !== "skipped");
	const skipped = job.results.length - converted.length;
	// Converted items are done; the skipped ones stay selected so they can be retried or trashed.
	deselect(converted.map((r) => r.relative_path));
	if (converted.length === 0) {
		showBatchAlert({
			title: download ? "Nothing could be zipped" : "Nothing could be converted",
			percent: null,
			lines: skippedLines(job.results),
		});
		return;
	}
	showBatchAlert({
		title:
			skipped === 0
				? "All " + String(converted.length) + " " + verb
				: String(converted.length) +
					" of " +
					String(job.results.length) +
					" " +
					verb +
					" · " +
					String(skipped) +
					" skipped",
		detail: download ? DOWNLOAD_NOTE : CONVERT_NOTE,
		percent: null,
		lines: skippedLines(job.results),
		canDownload: Boolean(job.download_url),
	});
	currentZipUrl = job.download_url;
}
let currentZipUrl = "";
const ZIP_NAME = "SpaceMaker-export.zip";

function saveZip(url: string): void {
	currentZipUrl = "";
	batchPollToken += 1;
	const token = batchPollToken;
	const live = (fn: () => void): void => {
		if (token === batchPollToken) {
			fn();
		}
	};
	void saveOnDesktop(url, ZIP_NAME, {
		onProgress: (percent, text) =>
			live(() => {
				showBatchAlert({ title: "Saving " + ZIP_NAME + "… " + String(percent) + "%", detail: text, percent });
			}),
		onDone: (path) =>
			live(() => {
				showBatchAlert({ title: "Saved", detail: path, percent: null });
			}),
		onError: (message) =>
			live(() => {
				showBatchAlert({ title: "Could not save the zip", detail: message, percent: null });
			}),
	}).then((started) => {
		if (!started) {
			currentZipUrl = url; // dialog cancelled: the zip stays available
		}
	});
}

function pollConvert(jobId: string, token: number): void {
	window.setTimeout(() => {
		if (token !== batchPollToken) {
			return;
		}
		apiGet<GalleryBatchConvertJob>("/api/gallery/batch/convert/" + encodeURIComponent(jobId))
			.then((job) => {
				if (token !== batchPollToken) {
					return;
				}
				applyConvertJob(job, token);
			})
			.catch((err: unknown) => {
				if (token !== batchPollToken) {
					return;
				}
				const gone = err instanceof ApiError && err.status === 404;
				showBatchAlert({
					title: gone ? "This conversion is no longer available" : "Could not check the conversion",
					detail: gone
						? "Run it again from the selection bar."
						: errorMessage(err, "Check your connection and try again."),
					percent: null,
				});
			});
	}, BATCH_POLL_MS);
}
function applyConvertJob(job: GalleryBatchConvertJob, token: number): void {
	if (job.phase === "running") {
		showConvertRunning(job);
		pollConvert(job.job_id, token);
	} else if (job.phase === "done") {
		showConvertFinished(job);
	} else if (job.phase === "error") {
		showBatchAlert({ title: "Conversion failed", detail: job.error || "Something went wrong.", percent: null });
	}
}

interface CpuConfirmDetail {
	code?: string;
	video_count?: number;
}
function cpuConfirmDetail(err: unknown): CpuConfirmDetail | null {
	if (!(err instanceof ApiError) || err.status !== 409) {
		return null;
	}
	const detail = err.detail as CpuConfirmDetail | null;
	return detail && detail.code === "cpu_confirm_required" ? detail : null;
}

async function startConvert(allowCpuEncode: boolean, endpoint = "/api/gallery/batch/convert"): Promise<void> {
	const paths = selectedPaths();
	setPanelVisible("gallery-cpu-confirm", false);
	if (!paths.length) {
		return;
	}
	batchPollToken += 1;
	const token = batchPollToken;
	try {
		const job = await apiSend<GalleryBatchConvertJob>("POST", endpoint, {
			relative_paths: paths,
			allow_cpu_encode: allowCpuEncode,
		});
		if (token !== batchPollToken) {
			return;
		}
		applyConvertJob(job, token);
	} catch (err) {
		const needsCpu = cpuConfirmDetail(err);
		if (needsCpu) {
			// Nothing started: ask once before using the CPU for the videos.
			const count = needsCpu.video_count ?? 1;
			const countEl = el("gallery-cpu-confirm-count");
			if (countEl) {
				countEl.textContent = String(count) + (count === 1 ? " video" : " videos");
			}
			setPanelVisible("gallery-cpu-confirm", true);
			return;
		}
		const lowDisk = err instanceof ApiError && err.status === 507;
		showBatchAlert({
			title: lowDisk
				? "Not enough free disk space"
				: endpoint.endsWith("/download")
					? "Could not prepare the download"
					: "Could not start the conversion",
			detail: lowDisk
				? "Free some space and try again. Nothing was written."
				: errorMessage(err, "Nothing was changed."),
			percent: null,
		});
	}
}

function bindGallerySelectUi(): void {
	onSelectionChange(refreshSelectionUi);
	onClick("btn-gallery-select", () => {
		setSelecting(!isSelecting());
	});
	onClick("btn-gallery-select-cancel", () => {
		setSelecting(false);
	});
	document.addEventListener("keydown", (ev) => {
		if (ev.key !== "Escape") {
			return;
		}
		const open = ["gallery-trash-confirm", "gallery-cpu-confirm"].filter(
			(id) => !el(id)?.classList.contains("panel-hidden"),
		);
		if (open.length) {
			// An open dialog takes Esc first; a second press leaves select mode.
			for (const id of open) {
				setPanelVisible(id, false);
			}
		} else if (isSelecting()) {
			setSelecting(false);
		}
	});
	onClick("btn-gallery-batch-trash", () => {
		const n = selectedCount();
		const title = el("gallery-trash-confirm-title");
		if (title) {
			title.textContent = "Move " + itemsLabel(n) + " to the Trash?";
		}
		setPanelVisible("gallery-cpu-confirm", false);
		setPanelVisible("gallery-trash-confirm", true);
	});
	onClick("btn-gallery-trash-cancel", () => {
		setPanelVisible("gallery-trash-confirm", false);
	});
	onClick("btn-gallery-trash-confirm", () => {
		void runTrash();
	});
	onClick("btn-gallery-batch-download", () => {
		setPanelVisible("gallery-trash-confirm", false);
		void startConvert(false, "/api/gallery/batch/download");
	});
	onClick("btn-gallery-batch-convert", () => {
		setPanelVisible("gallery-trash-confirm", false);
		void startConvert(false);
	});
	onClick("btn-gallery-cpu-continue", () => {
		void startConvert(true);
	});
	onClick("btn-gallery-cpu-cancel", () => {
		setPanelVisible("gallery-cpu-confirm", false);
	});
	onClick("btn-gallery-batch-dismiss", hideBatchAlert);
	onClick("btn-gallery-batch-zip", () => {
		if (!currentZipUrl) {
			return;
		}
		const url = currentZipUrl;
		if (canSaveOnDesktop()) {
			saveZip(url);
			return;
		}
		// A phone or plain browser shows its own download UI.
		triggerFileDownload(url);
		currentZipUrl = "";
		showBatchAlert({ title: "Download started", detail: "Check your browser's downloads.", percent: null });
	});
	refreshSelectionUi();
}

export { bindGallerySelectUi, refreshSelectionUi };
