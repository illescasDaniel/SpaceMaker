import { apiSend } from "./api.ts";
import { errorMessage, onClick } from "./dom.ts";
import { shiftGalleryItem, startFriendlyExport, triggerFileDownload } from "./gallery-item.ts";
import { loadCalendarMonth, loadGallery, removeGalleryThumb, shiftCalendarMonth } from "./gallery-timeline.ts";
import { showView } from "./shell.ts";
import { S } from "./state.ts";

function bindGalleryUi(): void {
	const btnTimeline = document.getElementById("btn-timeline");
	const btnCalendar = document.getElementById("btn-calendar");
	const timelineView = document.getElementById("timeline-view");
	const calendarView = document.getElementById("calendar-view");
	if (btnTimeline && btnCalendar && timelineView && calendarView) {
		btnTimeline.addEventListener("click", () => {
			btnTimeline.classList.add("active");
			btnCalendar.classList.remove("active");
			timelineView.style.display = "block";
			calendarView.classList.remove("visible");
			calendarView.setAttribute("aria-hidden", "true");
		});
		btnCalendar.addEventListener("click", () => {
			btnCalendar.classList.add("active");
			btnTimeline.classList.remove("active");
			timelineView.style.display = "none";
			calendarView.classList.add("visible");
			calendarView.setAttribute("aria-hidden", "false");
			loadCalendarMonth();
		});
	}
	onClick("btn-cal-prev", () => {
		shiftCalendarMonth(-1);
	});
	onClick("btn-cal-next", () => {
		shiftCalendarMonth(1);
	});
	onClick("btn-gallery-item-back", () => {
		showView("gallery");
	});
	onClick("btn-gallery-item-prev", () => {
		shiftGalleryItem(-1);
	});
	onClick("btn-gallery-item-next", () => {
		shiftGalleryItem(1);
	});
	onClick("btn-gallery-download", () => {
		if (!S.galleryItemPath) {
			return;
		}
		triggerFileDownload("/media/" + encodeURI(S.galleryItemPath) + "?download=1");
	});
	onClick("btn-gallery-open", () => {
		if (!S.galleryItemPath) {
			return;
		}
		apiSend("POST", "/api/gallery/open", { relative_path: S.galleryItemPath, target: "file" }).catch((err: unknown) => {
			window.alert(errorMessage(err, "Could not open this file."));
		});
	});
	onClick("btn-gallery-open-folder", () => {
		if (!S.galleryItemPath) {
			return;
		}
		apiSend("POST", "/api/gallery/open", { relative_path: S.galleryItemPath, target: "folder" }).catch(
			(err: unknown) => {
				window.alert(errorMessage(err, "Could not open the folder."));
			},
		);
	});
	onClick("btn-gallery-friendly", () => {
		if (!S.galleryItemPath) {
			return;
		}
		startFriendlyExport();
	});
	onClick("btn-gallery-delete", () => {
		if (!S.galleryItemPath) {
			return;
		}
		if (!window.confirm("Delete this file from processed/ on this computer? This cannot be undone.")) {
			return;
		}
		apiSend("DELETE", "/api/gallery/item?path=" + encodeURIComponent(S.galleryItemPath))
			.then(() => {
				const deletedPath = S.galleryItemPath;
				S.galleryItemPath = "";
				// Show the grid first, animate the deleted tile out, then re-sync from the server.
				showView("gallery", { skipGalleryReload: true });
				if (!removeGalleryThumb(deletedPath, loadGallery)) {
					loadGallery();
				}
			})
			.catch((err: unknown) => {
				window.alert(errorMessage(err, "Could not delete this file."));
			});
	});
}

export { bindGalleryUi };
