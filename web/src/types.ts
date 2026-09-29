/** Shared domain types for the SpaceMaker shell UI. */

export type ShellKind = "desktop" | "mobile_gallery";

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** Native file/folder pickers exposed by the pywebview desktop shell (absent in a plain browser tab —
 * every call site guards with `window.pywebview?.api?.<method>` before using it). */
export interface PywebviewApi {
	choose_library_folder?: (current: string) => Promise<string | null> | string | null;
	choose_device_files?: (mount: string) => Promise<string[] | null> | string[] | null;
	choose_device_folder?: (mount: string) => Promise<string | null> | string | null;
	choose_files?: (current: string) => Promise<string[] | null> | string[] | null;
	choose_share_folder?: (current: string) => Promise<string | null> | string | null;
	share_folder_file_count?: (folder: string) => Promise<number> | number;
}

declare global {
	interface Window {
		SPACEMAKER_SHELL?: ShellKind;
		SPACEMAKER_UI_SHELL_VERSION?: string;
		pywebview?: { api?: PywebviewApi };
	}
}

export type AppModuleId =
	| "home"
	| "photo_backup"
	| "usb_photo_backup"
	| "usb_file_transfer"
	| "receive_files"
	| "send_files"
	| "transfer_files";

export type ViewId =
	| "home"
	| "easy"
	| "wizard"
	| "usb-file-transfer"
	| "receive-files"
	| "send-files"
	| "transfer-files"
	| "gallery"
	| "gallery-item"
	| "settings"
	| "settings-tools"
	| "legal"
	| "components";

export interface ViewOptions {
	skipHistory?: boolean;
}

/** `{completed, total, percent}` counters shared by every long-running job phase
 * (mirrors `spacemaker.domain.library.JobProgress`, serialized in `session.py`'s `snapshot()`). */
export interface JobProgress {
	completed: number;
	total: number;
	percent: number;
}

/** One job's phase + progress, as read from `AppSnapshot.extract` / `.convert` / `.usb_transfer`. */
export interface JobPhaseState {
	phase: string;
	progress: JobProgress;
}

/** Action-button enablement flags (`spacemaker.application.wizard_state.wizard_actions` /
 * `spacemaker.domain.usb_file_transfer.transfer_control_flags`); every key is optional since
 * each job type only sets the flags relevant to it. */
export interface ControlFlags {
	start?: boolean;
	pause?: boolean;
	resume?: boolean;
	stop?: boolean;
}

export interface VisualizeState {
	enabled: boolean;
	phase: string;
	status_text: string;
}

export interface WifiUploadSnapshot {
	active: boolean;
	upload_url: string;
	qr_url: string;
}

export interface CompressMediaSnapshot {
	enabled: boolean;
	control_enabled: boolean;
	tools_available: boolean;
}

export interface UsbTransferBrowseSnapshot {
	mount_available?: boolean;
	mount_root?: string;
	hint?: string;
	available_folders?: string[] | null;
}

/** One row of `transfer_files_session.items` (`spacemaker.bootstrap.services.snapshots`'s
 * `_transfer_item_row`, mirrors `spacemaker.domain.transfer_session.TransferItemKind` / `TransferOrigin`). */
export interface TransferItem {
	id: string;
	name: string;
	kind: "file" | "folder_zip";
	origin: "pc" | "phone";
	origin_label: string;
	download_name: string;
}

/** Response of `POST /api/transfer/save` (`lan_sessions.py`'s `save_transfer_item_to_documents`). */
export interface TransferSaveResult {
	saved_path: string;
	saved_name: string;
	saved_path_display: string;
}

/** Shape shared by the receive-files / send-files / transfer-files LAN session snapshots
 * (`spacemaker.bootstrap.services.snapshots`'s `_receive_files_snapshot` / `_file_share_snapshot` /
 * `_transfer_files_snapshot`); each call site only sets the fields relevant to that session kind. */
export interface LanSessionSnapshot {
	active: boolean;
	page_url?: string;
	qr_url?: string;
	item_count?: number;
	items?: TransferItem[];
	file_count?: number;
}

/** One row of `spacemaker.application.managed_tools`'s `status_dict()["tools"]`. */
export interface ToolStatusRow {
	tool_id: string;
	phase: string;
	resolution: string;
	path: string;
	message: string;
}

/** Windows-only winget install hint from `spacemaker.bootstrap.platform_setup_hints.components_setup_hint`. */
export interface ComponentsSetupHint {
	title: string;
	detail: string;
	command: string;
}

export interface ManagedToolsStatus {
	tools_dir: string;
	all_ready: boolean;
	downloads_pending: boolean;
	setup_pending: boolean;
	tools: ToolStatusRow[];
	setup_hint?: ComponentsSetupHint;
}

/** Per-`LibraryFolder` file counts (`spacemaker.domain.library.LibraryFolder`: originals/processed/error/invalid). */
export interface LibraryCounts {
	originals?: number;
	processed?: number;
	error?: number;
	invalid?: number;
}

/** API snapshot payload — structural typing for fields the shell actually reads.
 * The backend routes only promise `dict[str, object]` (see `routes/settings.py`,
 * `routes/gallery.py`), so this models the frontend's contract with the payload rather
 * than the full backend shape; the index signature covers everything else untouched. */
export interface AppSnapshot {
	ui_mode?: string;
	active_module?: AppModuleId;
	library_root?: string;
	library_root_display?: string;
	library_counts?: LibraryCounts;
	ui_shell_version?: string;
	app_author?: string;
	app_contact?: string;
	app_version?: string;
	connection_method?: string;
	device_id?: string;
	device_label?: string;
	source_folders?: string[];
	transfer_mode?: string;
	transfer_folders?: string[];
	transfer_extra_paths?: string[];
	share_selection?: string[];
	last_error?: string;
	hint?: string;
	mount_root?: string;
	receive_files?: JobPhaseState;
	extract?: JobPhaseState;
	extract_controls?: ControlFlags;
	extract_stopping?: boolean;
	convert?: JobPhaseState;
	convert_controls?: ControlFlags;
	can_start_convert?: boolean;
	visualize?: VisualizeState;
	usb_transfer?: JobPhaseState;
	usb_transfer_actions?: ControlFlags;
	usb_transfer_browse?: UsbTransferBrowseSnapshot;
	usb_transfer_available_folders?: string[] | null;
	usb_transfer_iphone_limit?: boolean;
	usb_transfer_show_open_folder?: boolean;
	image_import_issues?: { errors: number; invalid: number };
	video_friendly_export_available?: boolean;
	managed_tools?: ManagedToolsStatus;
	tools_ready?: boolean;
	tools_downloads_pending?: boolean;
	tools_setup_pending?: boolean;
	missing_tools?: string[];
	wifi_upload?: WifiUploadSnapshot;
	receive_files_session?: LanSessionSnapshot;
	file_share?: LanSessionSnapshot;
	transfer_files_session?: LanSessionSnapshot;
	documents_receive_root?: string;
	documents_receive_root_display?: string;
	documents_receive_file_count?: number;
	compress_media?: CompressMediaSnapshot;
}

export interface Defaults {
	default_library_root: string;
}

/** One row of `GET /api/devices` (`routes/extract.py`'s `list_devices`). */
export interface DeviceRow {
	device_id: string;
	label: string;
}

export interface GalleryNeighbor {
	prev: string | null;
	next: string | null;
}

export interface FormValidation {
	ok: boolean;
	library: string;
	device: string;
	folders: string;
}

/** One row from `_gallery_item_dict` (`adapters/inbound/web/serializers.py`'s `gallery_item_dict`;
 * mirrors `spacemaker.domain.media.MediaKind`). */
export interface GalleryItem {
	relative_path: string;
	captured_at: string;
	kind: "image" | "video" | "unsupported";
}

/** One page of `GET /api/gallery/timeline` (`routes/gallery.py`'s `gallery_timeline`). */
export interface GalleryTimelinePage {
	items: GalleryItem[];
	next_cursor: string | null;
}

/** `GET /api/gallery/calendar` (`routes/gallery.py`'s `gallery_calendar`). */
export interface GalleryCalendarResponse {
	year: number;
	month: number;
	days_with_media: number[];
}

/** `GET /api/gallery/day` (`routes/gallery.py`'s `gallery_day`). */
export interface GalleryDayResponse {
	year: number;
	month: number;
	day: number;
	items: GalleryItem[];
}

/** `spacemaker.bootstrap.firewall.FirewallStatus`, serialized as-is by `routes/settings.py`'s `server_info`. */
export interface FirewallStatus {
	backend: string | null;
	active: boolean | null;
	port_open: boolean | null;
	lan_connect_ok: boolean | null;
	message: string;
}

/** `GET /api/server-info` (`routes/settings.py`'s `server_info`). */
export interface ServerInfo {
	host: string;
	port: number;
	gallery_url: string;
	qr_url: string;
	lan_listening: boolean;
	lan_reachable: boolean;
	firewall: FirewallStatus;
}

/** `adapters/inbound/web/serializers.py`'s `GalleryMetadataPayload` (from `metadata_dict`). */
export interface GalleryMetadata {
	filename: string;
	captured_at: string | null;
	camera_make: string;
	camera_model: string;
	width: number | null;
	height: number | null;
	duration_seconds: number | null;
	file_size_bytes: number;
	gps: string;
}

/** `GET /api/gallery/item` (`routes/gallery.py`'s `gallery_item_detail`). */
export interface GalleryItemDetail {
	relative_path: string;
	absolute_path: string;
	captured_at: string;
	kind: "image" | "video" | "unsupported";
	preview_in_browser: boolean;
	metadata: GalleryMetadata;
}

/** `spacemaker.domain.gallery_export_job.GalleryExportJob.to_dict()` — the `POST /api/gallery/export`
 * response and the payload of the WS `{"type": "gallery_export", "export": ...}` message
 * (`bootstrap/services/jobs.py`'s `push_gallery_export`). */
export interface GalleryExportJob {
	job_id: string;
	relative_path: string;
	format: string;
	phase: "idle" | "running" | "done" | "error";
	percent: number;
	download_url: string;
	error: string;
	skipped_encode: boolean;
}

/** One rendered/collapsed month section of the gallery timeline (client-side windowing state;
 * not backend data — see `gallery-timeline.ts`'s `appendGalleryTimelineItems`/`unmountGalleryMonthBlock`). */
export interface GalleryMonthBlock {
	year: number;
	month: number;
	showYear: boolean;
	items: GalleryItem[];
	el: HTMLElement | null;
	placeholderEl: HTMLElement | null;
	mounted: boolean;
}
