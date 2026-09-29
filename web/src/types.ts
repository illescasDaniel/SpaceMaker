/** Shared domain types for the SpaceMaker shell UI. */

export type ShellKind = "desktop" | "mobile_gallery";

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

declare global {
	interface Window {
		SPACEMAKER_SHELL?: ShellKind;
		SPACEMAKER_UI_SHELL_VERSION?: string;
	}
}

/** API snapshot payload — structural typing for fields the shell reads. */
export interface AppSnapshot {
	ui_mode?: string;
	library_root?: string;
	ui_shell_version?: string;
	[key: string]: JsonValue | undefined;
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

export interface GalleryMonthBlock {
	key: string;
	el: HTMLElement;
	tileCount: number;
	mounted: boolean;
}

/**
 * Runtime registry filled by feature modules. Core modules type the helpers they
 * define; feature modules remain progressively typed (@ts-nocheck until migrated).
 */
export interface RuntimeRegistry {
	api?: (method: string, path: string, body?: unknown) => Promise<unknown>;
	apiSend?: (url: string, method?: string, body?: unknown) => Promise<unknown>;
	apiGet?: (path: string) => Promise<unknown>;
	formatApiError?: (item: unknown) => string;
	isDesktopShell?: () => boolean;
	isMobileGalleryShell?: () => boolean;
	onClick?: (id: string, handler: (ev: MouseEvent) => void) => void;
	isAbsolutePath?: (path: string) => boolean;
	showFormBanner?: (message: string, bannerId?: string) => void;
	clearFormBanner?: (bannerId?: string) => void;
	setStatusLine?: (el: HTMLElement | null, detailText: string) => void;
	bindDisclosure?: (btnId: string, panelId: string) => void;
	bindInfoPanelToggle?: (btnId: string, panelId: string) => void;
	setQrUrlField?: (inputId: string, url: string) => void;
	setQrImage?: (img: HTMLImageElement | null, qrUrl: string, cacheKey?: string) => void;
	setQrImageSrc?: (img: HTMLImageElement | null, qrUrl: string, cacheKey?: string) => void;
	bootstrapMobileGalleryShell?: () => void;
	bootstrapDesktopShell?: () => void;
	[key: string]: ((...args: never[]) => unknown) | undefined;
}
