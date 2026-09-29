/** Shared shell state. */
function initialShell() {
	if (typeof window !== "undefined" && window.SPACEMAKER_SHELL) {
		return window.SPACEMAKER_SHELL;
	}
	return "desktop";
}
export const S = {
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
