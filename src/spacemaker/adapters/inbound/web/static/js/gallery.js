// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

function bindGalleryUi() {
	var btnTimeline = document.getElementById("btn-timeline");
	var btnCalendar = document.getElementById("btn-calendar");
	var timelineView = document.getElementById("timeline-view");
	var calendarView = document.getElementById("calendar-view");
	if (btnTimeline && btnCalendar && timelineView && calendarView) {
		btnTimeline.addEventListener("click", function () {
			btnTimeline.classList.add("active");
			btnCalendar.classList.remove("active");
			timelineView.style.display = "block";
			calendarView.classList.remove("visible");
			calendarView.setAttribute("aria-hidden", "true");
		});
		btnCalendar.addEventListener("click", function () {
			btnCalendar.classList.add("active");
			btnTimeline.classList.remove("active");
			timelineView.style.display = "none";
			calendarView.classList.add("visible");
			calendarView.setAttribute("aria-hidden", "false");
			R.loadCalendarMonth();
		});
	}
	R.onClick("btn-cal-prev", function () {
		R.shiftCalendarMonth(-1);
	});
	R.onClick("btn-cal-next", function () {
		R.shiftCalendarMonth(1);
	});
	R.onClick("btn-gallery-item-back", function () {
		R.showView("gallery");
	});
	R.onClick("btn-gallery-item-prev", function () {
		R.shiftGalleryItem(-1);
	});
	R.onClick("btn-gallery-item-next", function () {
		R.shiftGalleryItem(1);
	});
	R.onClick("btn-gallery-download", function () {
		if (!S.galleryItemPath) {
			return;
		}
		R.triggerFileDownload("/media/" + encodeURI(S.galleryItemPath) + "?download=1");
	});
	R.onClick("btn-gallery-open", function () {
		if (!S.galleryItemPath) {
			return;
		}
		R.api("POST", "/api/gallery/open", { relative_path: S.galleryItemPath, target: "file" }).catch(function (err) {
			window.alert(err.message || "Could not open this file.");
		});
	});
	R.onClick("btn-gallery-open-folder", function () {
		if (!S.galleryItemPath) {
			return;
		}
		R.api("POST", "/api/gallery/open", { relative_path: S.galleryItemPath, target: "folder" }).catch(function (err) {
			window.alert(err.message || "Could not open the folder.");
		});
	});
	R.onClick("btn-gallery-friendly", function () {
		if (!S.galleryItemPath) {
			return;
		}
		R.startFriendlyExport();
	});
	R.onClick("btn-gallery-delete", function () {
		if (!S.galleryItemPath) {
			return;
		}
		if (!window.confirm("Delete this file from processed/ on this computer? This cannot be undone.")) {
			return;
		}
		R.api("DELETE", "/api/gallery/item?path=" + encodeURIComponent(S.galleryItemPath))
			.then(function () {
				S.galleryItemPath = "";
				R.showView("gallery");
			})
			.catch(function (err) {
				window.alert(err.message || "Could not delete this file.");
			});
	});
}
R.bindGalleryUi = bindGalleryUi;

export { bindGalleryUi };
