import { isMobileGalleryShell } from "./dom.ts";
import { bootstrapDesktopShell, bootstrapMobileGalleryShell } from "./shell.ts";

if (isMobileGalleryShell()) {
	bootstrapMobileGalleryShell();
} else {
	bootstrapDesktopShell();
}
