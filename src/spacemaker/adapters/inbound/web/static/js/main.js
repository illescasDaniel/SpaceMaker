import { isMobileGalleryShell } from "./dom.js";
import { bootstrapDesktopShell, bootstrapMobileGalleryShell } from "./shell.js";

if (isMobileGalleryShell()) {
	bootstrapMobileGalleryShell();
} else {
	bootstrapDesktopShell();
}
