import "./dom.js";
import "./api.js";
import "./settings.js";
import "./lan.js";
import "./jobs.js";
import "./home.js";
import "./home-bind.js";
import "./usb.js";
import "./gallery-item.js";
import "./gallery-timeline.js";
import "./gallery.js";
import "./shell-chrome.js";
import "./shell-boot.js";
import "./shell.js";
import "./ws.js";
import { R } from "./state.js";

const isMobile = R.isMobileGalleryShell;
const bootMobile = R.bootstrapMobileGalleryShell;
const bootDesktop = R.bootstrapDesktopShell;
if (isMobile?.()) {
	bootMobile?.();
} else {
	bootDesktop?.();
}
