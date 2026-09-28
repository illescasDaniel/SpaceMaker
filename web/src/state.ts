/** Shared shell state and runtime registry. */

import type {
	AppSnapshot,
	FormValidation,
	GalleryMonthBlock,
	GalleryNeighbor,
	RuntimeRegistry,
	ShellKind,
} from "./types.js";

export interface ShellState {
	clientShell: ShellKind;
	uiMode: string;
	state: AppSnapshot | null;
	deviceLabels: Record<string, string>;
	defaultLibraryRoot: string;
	formValidation: FormValidation;
	calendarYear: number;
	calendarMonth: number;
	calendarSelectedDay: number | null;
	galleryItemPath: string;
	galleryItemKind: string;
	galleryItemNeighbors: GalleryNeighbor;
	galleryMonthBlocks: GalleryMonthBlock[];
	galleryNextCursor: string | null;
	galleryHasMore: boolean;
	galleryLoadingMore: boolean;
	galleryMountedTileCount: number;
	galleryWindowListenersBound: boolean;
	galleryWindowCheckScheduled: boolean;
	galleryIntersectionObserver: IntersectionObserver | null;
	GALLERY_PAGE_LIMIT: number;
	GALLERY_TILE_BUDGET: number;
	GALLERY_VIEWPORT_BUFFER_MULTIPLIER: number;
	lastQrSrcByElementId: Record<string, string>;
	uftFoldersMethod: string;
	uftAvailableFoldersKey: string;
	COMPONENTS_DISMISS_KEY: string;
}

function initialShell(): ShellKind {
	if (typeof window !== "undefined" && window.SPACEMAKER_SHELL) {
		return window.SPACEMAKER_SHELL;
	}
	return "desktop";
}

export const S: ShellState = {
	clientShell: initialShell(),
	uiMode: "easy",
	state: null,
	deviceLabels: {},
	defaultLibraryRoot: "",
	formValidation: { ok: false, library: "", device: "", folders: "" },
	calendarYear: new Date().getFullYear(),
	calendarMonth: new Date().getMonth() + 1,
	calendarSelectedDay: null,
	galleryItemPath: "",
	galleryItemKind: "image",
	galleryItemNeighbors: { prev: null, next: null },
	galleryMonthBlocks: [],
	galleryNextCursor: null,
	galleryHasMore: false,
	galleryLoadingMore: false,
	galleryMountedTileCount: 0,
	galleryWindowListenersBound: false,
	galleryWindowCheckScheduled: false,
	galleryIntersectionObserver: null,
	GALLERY_PAGE_LIMIT: 150,
	GALLERY_TILE_BUDGET: 1200,
	GALLERY_VIEWPORT_BUFFER_MULTIPLIER: 3,
	lastQrSrcByElementId: {},
	uftFoldersMethod: "",
	uftAvailableFoldersKey: "",
	COMPONENTS_DISMISS_KEY: "spacemaker_components_continue",
};

/** Filled by feature modules at import time; typed bag, not `any`. */
export const R: RuntimeRegistry = {};
