(function () {
	var clientShell = window.SPACEMAKER_SHELL || "desktop";
	var EXPECTED_UI_SHELL_VERSION = "2026.09.gallery-nav";
	var lastMainView = "home";
	var uiMode = "easy";
	var state = null;

	function isDesktopShell() {
		return clientShell === "desktop";
	}

	function isMobileGalleryShell() {
		return clientShell === "mobile_gallery";
	}

	function onClick(id, handler) {
		var el = document.getElementById(id);
		if (el) {
			el.addEventListener("click", handler);
		}
	}
	var deviceLabels = {};
	var defaultLibraryRoot = "";
	var formValidation = { ok: false, library: "", device: "", folders: "" };
	var calendarYear = new Date().getFullYear();
	var calendarMonth = new Date().getMonth() + 1;
	var calendarSelectedDay = null;
	var galleryItemPath = "";
	var galleryItemKind = "image";
	var galleryItemNeighbors = { prev: null, next: null };
	var galleryMonthBlocks = [];
	var galleryNextCursor = null;
	var galleryHasMore = false;
	var galleryLoadingMore = false;
	var galleryMountedTileCount = 0;
	var galleryWindowListenersBound = false;
	var galleryWindowCheckScheduled = false;
	var galleryIntersectionObserver = null;
	var GALLERY_PAGE_LIMIT = 150;
	var GALLERY_TILE_BUDGET = 1200;
	var GALLERY_VIEWPORT_BUFFER_MULTIPLIER = 3;
	var lastQrSrcByElementId = {};
	function isAbsolutePath(path) {
		if (!path) {
			return false;
		}
		return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path);
	}

	function showFormBanner(message) {
		var banner = document.getElementById("form-banner");
		if (!banner) {
			return;
		}
		banner.textContent = message;
		banner.hidden = !message;
	}

	function clearFormBanner() {
		showFormBanner("");
	}

	function setStatusLine(el, detailText) {
		if (!el) {
			return;
		}
		el.textContent = "";
		var strong = document.createElement("strong");
		strong.textContent = "Status:";
		el.appendChild(strong);
		el.appendChild(document.createTextNode(" " + detailText));
	}

	function setStageLoading(stage, direction) {
		if (!stage) {
			return;
		}
		stage.textContent = "";
		var media = document.createElement("div");
		media.className = "gallery-item-media";
		media.id = "gallery-item-media";
		if (direction === "next") {
			media.classList.add("slide-in-next-start");
		} else if (direction === "prev") {
			media.classList.add("slide-in-prev-start");
		}
		var thumb = document.createElement("img");
		thumb.className = "gallery-item-thumb";
		thumb.alt = "";
		thumb.setAttribute("aria-hidden", "true");
		thumb.src = "/thumbs/" + encodeURI(galleryItemPath);
		var spinner = document.createElement("div");
		spinner.className = "gallery-item-spinner";
		spinner.setAttribute("aria-hidden", "true");
		media.appendChild(thumb);
		media.appendChild(spinner);
		stage.appendChild(media);
		if (direction) {
			// Force layout so the slide-in-start transform applies before we clear it,
			// otherwise the browser coalesces both states and skips the animation.
			void media.offsetWidth;
			media.classList.remove("slide-in-next-start", "slide-in-prev-start");
		}
	}

	function setStageMessage(stage, message) {
		if (!stage) {
			return;
		}
		stage.textContent = "";
		var p = document.createElement("p");
		p.className = "status-line";
		p.textContent = message;
		stage.appendChild(p);
	}

	function renderGalleryItemStage(stage, payload, meta) {
		if (!stage) {
			return;
		}
		var media = stage.querySelector(".gallery-item-media");
		if (!media) {
			return;
		}
		media.querySelectorAll(".gallery-item-full, .gallery-no-preview").forEach(function (el) {
			el.remove();
		});
		var thumb = media.querySelector(".gallery-item-thumb");
		var spinner = media.querySelector(".gallery-item-spinner");
		var mediaUrl = "/media/" + encodeURI(payload.relative_path);
		var label = meta.filename || payload.relative_path;
		var video;
		var noPreview;
		var full;
		function reveal() {
			full.classList.add("loaded");
			if (thumb) {
				thumb.classList.add("hidden");
			}
			if (spinner) {
				spinner.classList.add("hidden");
			}
		}
		if (payload.kind === "video") {
			if (payload.preview_in_browser) {
				video = document.createElement("video");
				video.className = "gallery-item-full";
				video.controls = true;
				video.preload = "metadata";
				video.setAttribute("aria-label", label);
				full = video;
				video.addEventListener("loadeddata", reveal, { once: true });
				video.src = mediaUrl;
				media.appendChild(video);
			} else {
				noPreview = document.createElement("p");
				noPreview.className = "status-line gallery-no-preview";
				noPreview.textContent =
					"No in-browser preview for this codec (e.g. HEVC). Use Open on desktop or download the file.";
				media.appendChild(noPreview);
				if (spinner) {
					spinner.classList.add("hidden");
				}
			}
			return;
		}
		full = document.createElement("img");
		full.className = "gallery-item-full";
		full.alt = label;
		full.addEventListener("load", reveal, { once: true });
		full.src = mediaUrl;
		media.appendChild(full);
	}

	function warnIfStaleShell(settings) {
		var homeBanner;
		if (!isDesktopShell() || !settings) {
			return;
		}
		if (settings.ui_shell_version === EXPECTED_UI_SHELL_VERSION) {
			homeBanner = document.getElementById("home-form-banner");
			if (homeBanner) {
				homeBanner.hidden = true;
				homeBanner.textContent = "";
			}
			return;
		}
		var port = location.port || "8765";
		var message =
			"UI and server do not match. Quit every SpaceMaker window, stop any process on port " +
			port +
			", then run: uv run task spacemaker";
		homeBanner = document.getElementById("home-form-banner");
		if (homeBanner) {
			homeBanner.textContent = message;
			homeBanner.hidden = false;
		} else {
			showFormBanner(message);
		}
	}

	function syncActiveModuleView(next) {
		if (!isDesktopShell() || !next || toolsBlockMainApp(next)) {
			return;
		}
		var active = document.querySelector(".screen.active");
		if (!active?.id) {
			return;
		}
		if (active.id === "view-components") {
			return;
		}
		var currentId = active.id.replace(/^view-/, "");
		if (currentId === "gallery" || currentId === "gallery-item" || currentId === "settings" || currentId === "legal") {
			return;
		}
		var target = !next.active_module || next.active_module === "home" ? "home" : moduleToViewId(next.active_module);
		if (currentId !== target) {
			showView(target, { skipHistory: true });
		}
	}

	function selectedConnectionMethod() {
		var btnWifi = document.getElementById("btn-conn-wifi");
		if (!btnWifi) {
			return "wifi";
		}
		if (btnWifi.classList.contains("active")) {
			return "wifi";
		}
		if (document.getElementById("btn-conn-adb").classList.contains("active")) {
			return "adb";
		}
		if (document.getElementById("btn-conn-afc").classList.contains("active")) {
			return "afc";
		}
		return "mtp";
	}

	function validateStep1Form(showFieldErrors) {
		var lib = document.getElementById("input-library-root");
		var sel = document.getElementById("select-device");
		var libraryPath = lib ? lib.value.trim() : "";
		if (!libraryPath && state && state.library_root) {
			libraryPath = state.library_root;
		}
		var folders = selectedFolders();
		var method = selectedConnectionMethod();
		var deviceOk = method === "wifi" || !!sel?.value;
		var libraryOk = isAbsolutePath(libraryPath);
		var foldersOk = method === "wifi" || folders.length > 0;
		var libErr = document.getElementById("library-root-error");
		if (showFieldErrors && lib) {
			lib.classList.toggle("field-invalid", !libraryOk);
			lib.setAttribute("aria-invalid", libraryOk ? "false" : "true");
		}
		if (libErr) {
			if (!libraryOk && showFieldErrors) {
				libErr.hidden = false;
				libErr.textContent = libraryPath
					? "Enter a full absolute path (e.g. " + defaultLibraryRoot + ")."
					: "Choose a library folder with Browse or enter an absolute path.";
			} else {
				libErr.hidden = true;
			}
		}
		formValidation = {
			ok: libraryOk && deviceOk && foldersOk,
			library: libraryOk ? "" : "library",
			device: deviceOk ? "" : "device",
			folders: foldersOk ? "" : "folders",
		};
		return formValidation;
	}

	function api(method, path, body) {
		var opts = { method: method, headers: { Accept: "application/json" } };
		if (body !== undefined) {
			opts.headers["Content-Type"] = "application/json";
			opts.body = JSON.stringify(body);
		}
		return fetch(path, opts).then(function (r) {
			if (!r.ok) {
				return r.text().then(function (text) {
					var message = r.statusText;
					var j;
					if (text) {
						try {
							j = JSON.parse(text);
							if (typeof j.detail === "string") {
								message = j.detail;
							} else if (Array.isArray(j.detail)) {
								message = j.detail
									.map(function (item) {
										return item.msg || String(item);
									})
									.join("; ");
							}
						} catch (_parseErr) {
							if (text.length < 300) {
								message = text;
							}
						}
					}
					throw new Error(message);
				});
			}
			return r.json();
		});
	}

	function moduleToViewId(module) {
		switch (module) {
			case "photo_backup":
				return "easy";
			case "usb_photo_backup":
				return "wizard";
			case "receive_files":
				return "receive-files";
			case "send_files":
				return "send-files";
			case "transfer_files":
				return "transfer-files";
			default:
				return "home";
		}
	}

	function homeViewId() {
		if (!state?.active_module || state.active_module === "home") {
			return "home";
		}
		return moduleToViewId(state.active_module);
	}

	function isMainHubView(resolved) {
		return (
			resolved === "home" ||
			resolved === "easy" ||
			resolved === "wizard" ||
			resolved === "receive-files" ||
			resolved === "send-files" ||
			resolved === "transfer-files"
		);
	}

	function enterModule(moduleId) {
		return api("POST", "/api/module/enter", { module: moduleId })
			.then(applyState)
			.then(function () {
				showView(moduleToViewId(moduleId));
			})
			.catch(function (err) {
				showFormBanner(err.message || "Could not open this module.");
			});
	}

	function goHomeHub() {
		return api("POST", "/api/module/home")
			.then(applyState)
			.then(function () {
				showView("home");
			})
			.catch(function (err) {
				showFormBanner(err.message || "Could not return to Home.");
			});
	}

	function easyFileCountLabel(count, singular, plural) {
		if (count === 1) {
			return "1 " + singular;
		}
		return count + " " + plural;
	}

	function _setUiMode(mode, options) {
		options = options || {};
		uiMode = mode === "advanced" ? "advanced" : "easy";
		var btnEasy = document.getElementById("btn-ui-easy");
		var btnAdvanced = document.getElementById("btn-ui-advanced");
		var active;
		if (btnEasy) {
			btnEasy.classList.toggle("active", uiMode === "easy");
		}
		if (btnAdvanced) {
			btnAdvanced.classList.toggle("active", uiMode === "advanced");
		}
		if (!options.skipViewSwitch && !toolsBlockMainApp(state)) {
			active = document.querySelector(".screen.active");
			if (active && (active.id === "view-easy" || active.id === "view-wizard")) {
				showView("home", { skipHistory: true });
			}
		}
	}

	function setUiModeFromState(next) {
		uiMode = next.ui_mode === "advanced" ? "advanced" : "easy";
	}

	function pathForMainView(viewId) {
		if (viewId === "gallery") {
			return "/gallery";
		}
		if (viewId === "home" || viewId === "easy" || viewId === "wizard") {
			return "/";
		}
		return null;
	}

	function galleryItemPathFromLocation() {
		var prefix = "/gallery/item/";
		if (location.pathname.indexOf(prefix) !== 0) {
			return "";
		}
		return decodeURIComponent(location.pathname.slice(prefix.length));
	}

	function closeGalleryPhonePopup() {
		var popup = document.getElementById("gallery-phone-popup");
		var fab = document.getElementById("btn-gallery-phone-help");
		if (popup) {
			popup.classList.add("panel-hidden");
		}
		if (fab) {
			fab.setAttribute("aria-expanded", "false");
		}
	}

	function toggleGalleryPhonePopup() {
		var popup = document.getElementById("gallery-phone-popup");
		var fab = document.getElementById("btn-gallery-phone-help");
		if (!popup || !fab) {
			return;
		}
		var open = popup.classList.contains("panel-hidden");
		popup.classList.toggle("panel-hidden", !open);
		fab.setAttribute("aria-expanded", open ? "true" : "false");
	}

	function syncGalleryPhoneHelpVisibility(resolvedViewId) {
		var fab = document.getElementById("btn-gallery-phone-help");
		if (!fab || !isDesktopShell()) {
			return;
		}
		var onGallery = resolvedViewId === "gallery" || resolvedViewId === "gallery-item";
		fab.hidden = !onGallery;
		if (!onGallery) {
			closeGalleryPhonePopup();
		}
	}

	function showView(viewId, options) {
		var path;
		var itemPath;
		var resolved = viewId;
		options = options || {};
		if (viewId === "home") {
			resolved = "home";
		}
		document.querySelectorAll(".screen").forEach(function (s) {
			s.classList.remove("active");
		});
		document.getElementById("view-" + resolved).classList.add("active");
		syncGalleryPhoneHelpVisibility(resolved);
		if (isMainHubView(resolved) || resolved === "gallery" || resolved === "gallery-item") {
			document.querySelectorAll(".view-tabs button").forEach(function (b) {
				var tab = b.getAttribute("data-view");
				b.classList.toggle(
					"active",
					(tab === "gallery" && resolved.indexOf("gallery") === 0) || (tab === "home" && isMainHubView(resolved)),
				);
			});
			if (isMainHubView(resolved) || resolved === "gallery") {
				lastMainView = resolved === "gallery" ? "gallery" : "home";
				if (resolved === "gallery") {
					loadGallery();
				}
			}
			if (!options.skipHistory) {
				if (resolved === "gallery-item" && galleryItemPath) {
					itemPath = "/gallery/item/" + encodeURI(galleryItemPath);
					if (location.pathname !== itemPath) {
						history.pushState({ view: "gallery-item", path: galleryItemPath }, "", itemPath);
					}
				} else {
					path = pathForMainView(isMainHubView(resolved) ? "home" : resolved);
					if (path !== null && location.pathname !== path) {
						history.pushState({ view: resolved }, "", path);
					}
				}
			}
		}
	}

	function fetchGalleryNeighbor(path, direction) {
		return api("GET", "/api/gallery/item/neighbor?path=" + encodeURIComponent(path) + "&direction=" + direction)
			.then(function (payload) {
				return payload.relative_path || null;
			})
			.catch(function () {
				return null;
			});
	}

	function refreshGalleryItemNeighbors(path) {
		return Promise.all([fetchGalleryNeighbor(path, "prev"), fetchGalleryNeighbor(path, "next")]).then(
			function (results) {
				if (path !== galleryItemPath) {
					return; // a newer navigation started while these were in flight
				}
				galleryItemNeighbors = { prev: results[0], next: results[1] };
				updateGalleryItemNav();
			},
		);
	}

	function updateGalleryItemNav() {
		var prevBtn = document.getElementById("btn-gallery-item-prev");
		var nextBtn = document.getElementById("btn-gallery-item-next");
		if (!prevBtn || !nextBtn) {
			return;
		}
		prevBtn.disabled = !galleryItemNeighbors.prev;
		nextBtn.disabled = !galleryItemNeighbors.next;
	}

	function shiftGalleryItem(delta) {
		var direction = delta < 0 ? "prev" : "next";
		var target = delta < 0 ? galleryItemNeighbors.prev : galleryItemNeighbors.next;
		if (!target) {
			return;
		}
		var media = document.getElementById("gallery-item-media");
		var advance = function () {
			galleryItemPath = target;
			galleryItemNeighbors = { prev: null, next: null };
			updateGalleryItemNav();
			var itemPath = "/gallery/item/" + encodeURI(galleryItemPath);
			if (location.pathname !== itemPath) {
				history.pushState({ view: "gallery-item", path: galleryItemPath }, "", itemPath);
			}
			loadGalleryItemDetail(direction);
			refreshGalleryItemNeighbors(galleryItemPath);
		};
		if (media) {
			// Previous/Next only slides the preview — it doesn't replay the
			// container-level open animation that a fresh navigation gets.
			media.classList.add(direction === "next" ? "slide-out-next" : "slide-out-prev");
			window.setTimeout(advance, 160);
		} else {
			advance();
		}
	}

	function showGalleryItem(relativePath, options) {
		galleryItemPath = relativePath;
		galleryItemNeighbors = { prev: null, next: null };
		updateGalleryItemNav();
		showView("gallery-item", options || {});
		loadGalleryItemDetail();
		refreshGalleryItemNeighbors(relativePath);
	}

	function routeFromPath() {
		var itemPath = galleryItemPathFromLocation();
		if (itemPath) {
			showGalleryItem(itemPath, { skipHistory: true });
			return;
		}
		if (location.pathname === "/gallery") {
			showView("gallery", { skipHistory: true });
			return;
		}
		if (location.pathname === "/" || location.pathname === "") {
			showView(homeViewId(), { skipHistory: true });
		}
	}

	window.addEventListener("popstate", function () {
		routeFromPath();
	});

	function monthName(n) {
		return [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		][n - 1];
	}

	function connectionLabel(method) {
		if (method === "wifi") {
			return "Wi‑Fi";
		}
		if (method === "adb") {
			return "ADB";
		}
		if (method === "afc") {
			return "iPhone USB";
		}
		return "MTP";
	}

	function applyConnectionPanels(method) {
		var isWifi = method === "wifi";
		document.getElementById("panel-usb").classList.toggle("panel-hidden", isWifi);
		document.getElementById("panel-wifi").classList.toggle("panel-hidden", !isWifi);
		var chipMove = document.getElementById("chip-move");
		var chipCopy = document.getElementById("chip-copy");
		var moveHint = document.getElementById("move-wifi-hint");
		if (isWifi) {
			chipMove.classList.add("disabled");
			chipMove.disabled = true;
			chipCopy.classList.add("selected");
			chipMove.classList.remove("selected");
			if (moveHint) {
				moveHint.hidden = false;
			}
		} else {
			chipMove.classList.remove("disabled");
			chipMove.disabled = false;
			if (moveHint) {
				moveHint.hidden = true;
			}
		}
	}

	function syncConnectionButtons(method) {
		document.getElementById("btn-conn-wifi").classList.toggle("active", method === "wifi");
		document.getElementById("btn-conn-mtp").classList.toggle("active", method === "mtp");
		document.getElementById("btn-conn-adb").classList.toggle("active", method === "adb");
		document.getElementById("btn-conn-afc").classList.toggle("active", method === "afc");
		applyConnectionPanels(method);
	}

	function updateWifiUploadPanel(next) {
		var wifi = next.wifi_upload || {};
		var idle = document.getElementById("wifi-idle-hint");
		var live = document.getElementById("wifi-live-receive");
		var urlInput = document.getElementById("wifi-upload-url");
		var qrImg = document.getElementById("wifi-upload-qr");
		var wizardLibraryHint = document.getElementById("wizard-library-hint");
		var libDisplay = next.library_root_display || next.library_root;
		if (!idle || !live) {
			return;
		}
		if (wizardLibraryHint && libDisplay && (next.connection_method || "") === "wifi") {
			wizardLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
		} else if (wizardLibraryHint) {
			wizardLibraryHint.textContent = "";
		}
		setQrUrlField("wifi-qr-url-copy", wifi.upload_url || "");
		if (wifi.active) {
			idle.classList.add("panel-hidden");
			live.classList.remove("panel-hidden");
			if (urlInput) {
				urlInput.value = wifi.upload_url || "";
			}
			setQrImageSrc(qrImg, wifi.qr_url, "wifi-upload-qr");
		} else {
			idle.classList.remove("panel-hidden");
			live.classList.add("panel-hidden");
		}
	}

	function selectedFolders() {
		var boxes = document.querySelectorAll("#folder-picker input[type=checkbox]");
		var out = [];
		boxes.forEach(function (box) {
			if (box.checked && box.dataset.folder) {
				out.push(box.dataset.folder);
			}
		});
		return out;
	}

	function syncFolderCheckboxes(folders) {
		var set = new Set(folders || []);
		document.querySelectorAll("#folder-picker input[type=checkbox]").forEach(function (box) {
			if (box.dataset.folder) {
				box.checked = set.has(box.dataset.folder);
			}
		});
	}

	function updateDeviceStatus(next) {
		var root = document.getElementById("device-status");
		var textEl = document.getElementById("device-status-text");
		var name = "";
		if (!root || !textEl) {
			return;
		}
		var method = connectionLabel(next.connection_method);
		if (next.device_id && deviceLabels[next.device_id]) {
			name = deviceLabels[next.device_id];
			root.classList.add("connected");
			root.classList.remove("disconnected");
			textEl.textContent = name + " · Connected via " + method;
		} else {
			root.classList.remove("connected");
			root.classList.add("disconnected");
			textEl.textContent = "No device found · Check USB and " + method + " setup";
		}
	}

	function maybeShowMissingTools(next) {
		var missing = next.missing_tools || [];
		if (!missing.length) {
			return;
		}
		var banner = document.getElementById("form-banner");
		if (banner && !banner.hidden) {
			return;
		}
		showFormBanner(
			"Some components are missing (" + missing.join(", ") + "). Open Components setup or install them on your PATH.",
		);
	}

	var COMPONENTS_DISMISS_KEY = "spacemaker_components_continue";

	function toolsBlockMainApp(next) {
		return !!next?.tools_setup_pending;
	}

	function currentViewId() {
		var active = document.querySelector(".screen.active");
		return active ? active.id : "";
	}

	function toolDisplayName(toolId) {
		var labels = {
			adb: "adb",
			ffmpeg: "ffmpeg / ffprobe",
			ffprobe: "ffprobe",
			magick: "magick (ImageMagick)",
			exiftool: "exiftool",
			"mtp-detect": "mtp-detect (libmtp)",
			"mtp-getfile": "mtp-getfile (libmtp)",
			idevice_id: "idevice_id (libimobiledevice)",
			idevicepair: "idevicepair (libimobiledevice)",
			ideviceinfo: "ideviceinfo (libimobiledevice)",
			ifuse: "ifuse (libimobiledevice)",
		};
		return labels[toolId] || toolId;
	}

	function toolStatusText(tool) {
		if (tool.phase === "downloading" || tool.message === "Waiting for download") {
			return tool.phase === "downloading" ? "Downloading…" : "Waiting for download…";
		}
		if (tool.resolution === "managed") {
			return "Ready (downloaded)";
		}
		if (tool.resolution === "path") {
			return "Using system install (you chose Continue)";
		}
		if (tool.phase === "failed") {
			return tool.message || "Download failed";
		}
		return tool.message || "Not downloaded yet";
	}

	function fillToolStatusList(container, tools) {
		if (!container || !tools) {
			return;
		}
		container.innerHTML = "";
		tools.forEach(function (tool) {
			var row = document.createElement("div");
			row.className = "tool-row";
			var name = document.createElement("span");
			name.className = "tool-name";
			name.textContent = toolDisplayName(tool.tool_id);
			var status = document.createElement("span");
			status.className = "tool-status resolution-" + (tool.resolution || "missing");
			status.textContent = toolStatusText(tool);
			row.appendChild(name);
			row.appendChild(status);
			container.appendChild(row);
		});
	}

	function renderComponentsSetupHint(managedTools) {
		var el = document.getElementById("components-setup-hint");
		if (!el) {
			return;
		}
		var hint = managedTools?.setup_hint;
		var title;
		var detail;
		if (!hint?.command) {
			el.hidden = true;
			el.textContent = "";
			return;
		}
		el.hidden = false;
		el.replaceChildren();
		if (hint.title) {
			title = document.createElement("strong");
			title.textContent = hint.title;
			el.appendChild(title);
			el.appendChild(document.createElement("br"));
		}
		if (hint.detail) {
			detail = document.createElement("span");
			detail.textContent = hint.detail + " ";
			el.appendChild(detail);
		}
		var code = document.createElement("code");
		code.textContent = hint.command;
		el.appendChild(code);
	}

	function renderComponentsList(managedTools) {
		if (!managedTools?.tools) {
			return;
		}
		fillToolStatusList(document.getElementById("components-tool-list"), managedTools.tools);
		fillToolStatusList(document.getElementById("settings-tool-list"), managedTools.tools);
		renderComponentsSetupHint(managedTools);
		var settingsDir = document.getElementById("settings-managed-tools-dir");
		if (settingsDir && managedTools.tools_dir) {
			settingsDir.textContent = managedTools.tools_dir;
		}
	}

	function shouldPromptComponentsSetup(next) {
		if (!toolsBlockMainApp(next)) {
			sessionStorage.removeItem(COMPONENTS_DISMISS_KEY);
			return false;
		}
		if (sessionStorage.getItem(COMPONENTS_DISMISS_KEY) === "1") {
			return false;
		}
		return true;
	}

	function maybeShowComponentsScreen(next) {
		if (!shouldPromptComponentsSetup(next)) {
			return;
		}
		var viewId = currentViewId();
		if (viewId === "view-settings" || viewId === "view-legal") {
			renderComponentsList(next.managed_tools || {});
			return;
		}
		renderComponentsList(next.managed_tools || {});
		showView("components", { skipHistory: true });
		var continueBtn = document.getElementById("btn-components-continue");
		if (continueBtn) {
			continueBtn.disabled = false;
		}
	}

	function runComponentsEnsure() {
		return api("POST", "/api/tools/ensure").then(function (payload) {
			renderComponentsList(payload);
			return payload;
		});
	}

	function bindInfoPanelToggle(btnId, panelId) {
		onClick(btnId, function () {
			var panel = document.getElementById(panelId);
			var btn = document.getElementById(btnId);
			if (!panel || !btn) {
				return;
			}
			var open = !panel.classList.contains("visible");
			panel.classList.toggle("visible", open);
			panel.setAttribute("aria-hidden", open ? "false" : "true");
			btn.setAttribute("aria-expanded", open ? "true" : "false");
		});
	}

	function setQrUrlField(inputId, url) {
		var input = document.getElementById(inputId);
		if (input) {
			input.value = url || "";
		}
	}

	function setQrImageSrc(img, qrUrl, cacheKey) {
		if (!img) {
			return;
		}
		var key = cacheKey || img.id || "";
		if (!qrUrl) {
			delete lastQrSrcByElementId[key];
			return;
		}
		if (lastQrSrcByElementId[key] === qrUrl) {
			return;
		}
		lastQrSrcByElementId[key] = qrUrl;
		img.src = qrUrl + "&_=" + Date.now();
	}

	function updateReceiveUi(next) {
		var session = next.receive_files_session || {};
		var uploadQr = document.getElementById("receive-upload-qr");
		var uploadWait = document.getElementById("receive-upload-wait");
		var transferStatus = document.getElementById("receive-transfer-status");
		var transferFill = document.getElementById("receive-transfer-fill");
		var destHint = document.getElementById("receive-dest-hint");
		var rf = next.receive_files || {};
		var rp = rf.progress || { completed: 0, percent: 0, total: 0 };
		var transferPct;
		var fileCount;
		if (session.active && uploadQr) {
			uploadQr.hidden = false;
			if (session.qr_url) {
				uploadQr.src = session.qr_url + "&_=" + Date.now();
			}
			if (uploadWait) {
				uploadWait.hidden = true;
			}
		} else if (uploadQr) {
			uploadQr.hidden = true;
			if (uploadWait) {
				uploadWait.hidden = false;
				uploadWait.textContent = "Waiting to start receive session…";
			}
		}
		if (transferStatus) {
			transferStatus.textContent = easyFileCountLabel(rp.completed, "file received", "files received");
		}
		if (transferFill) {
			transferPct = rp.total > 0 ? rp.percent : rp.completed > 0 ? 100 : 0;
			transferFill.style.width = transferPct + "%";
		}
		var destDisplay = next.documents_receive_root_display || next.documents_receive_root;
		if (destHint && destDisplay) {
			destHint.textContent = "Files are saved under " + destDisplay;
		}
		var openWrap = document.getElementById("receive-open-wrap");
		if (openWrap) {
			fileCount = next.documents_receive_file_count;
			if (typeof fileCount !== "number") {
				fileCount = rp.completed;
			}
			openWrap.classList.toggle("panel-hidden", fileCount < 1);
		}
		setQrUrlField("receive-qr-url", session.page_url || "");
	}

	function updateSendUi(next) {
		var share = next.file_share || {};
		var paths = next.share_selection || [];
		var list = document.getElementById("share-path-list");
		var qrSection = document.getElementById("send-qr-section");
		var uploadQr = document.getElementById("send-share-qr");
		var serverHint = document.getElementById("send-server-only-hint");
		var hasDesktop = !!window.pywebview?.api;
		if (serverHint) {
			serverHint.classList.toggle("panel-hidden", hasDesktop);
		}
		if (list) {
			list.innerHTML = "";
			paths.forEach(function (p) {
				var li = document.createElement("li");
				li.textContent = p;
				list.appendChild(li);
			});
		}
		if (share.active && paths.length && qrSection && uploadQr) {
			qrSection.classList.remove("panel-hidden");
			uploadQr.hidden = false;
			if (share.qr_url) {
				uploadQr.src = share.qr_url + "&_=" + Date.now();
			}
			setQrUrlField("send-qr-url", share.page_url || "");
		} else if (qrSection && uploadQr) {
			qrSection.classList.add("panel-hidden");
			uploadQr.hidden = true;
			setQrUrlField("send-qr-url", "");
		}
	}

	function transferDownloadUrl(token, fileId) {
		return (
			"/api/transfer/download?t=" + encodeURIComponent(token || "") + "&file_id=" + encodeURIComponent(fileId || "")
		);
	}

	function updateTransferUi(next) {
		var session = next.transfer_files_session || {};
		var uploadQr = document.getElementById("transfer-qr");
		var uploadWait = document.getElementById("transfer-qr-wait");
		var list = document.getElementById("transfer-item-list");
		var status = document.getElementById("transfer-item-status");
		var serverHint = document.getElementById("transfer-server-only-hint");
		var hasDesktop = !!window.pywebview?.api;
		var items = session.items || [];
		var token = "";
		var pageUrl = session.page_url || "";
		if (pageUrl) {
			try {
				token = new URL(pageUrl).searchParams.get("t") || "";
			} catch (_err) {
				token = "";
			}
		}
		if (serverHint) {
			serverHint.classList.toggle("panel-hidden", hasDesktop);
		}
		if (session.active && uploadQr) {
			uploadQr.hidden = false;
			if (session.qr_url) {
				uploadQr.src = session.qr_url + "&_=" + Date.now();
			}
			if (uploadWait) {
				uploadWait.hidden = true;
			}
		} else if (uploadQr) {
			uploadQr.hidden = true;
			if (uploadWait) {
				uploadWait.hidden = false;
				uploadWait.textContent = "Waiting to start transfer session…";
			}
		}
		setQrUrlField("transfer-qr-url", pageUrl);
		if (list) {
			list.innerHTML = "";
			items.forEach(function (item) {
				var li = document.createElement("li");
				li.className = "transfer-item";
				var meta = document.createElement("span");
				meta.className = "transfer-item-meta";
				var name = document.createElement("span");
				name.className = "transfer-item-name";
				name.textContent = item.name || "";
				var from = document.createElement("span");
				from.className = "transfer-item-from";
				from.textContent =
					(item.kind === "folder_zip" ? "folder · " : "") +
					"from " +
					(item.origin_label || (item.origin === "pc" ? "PC" : "Phone"));
				meta.appendChild(name);
				meta.appendChild(from);
				var link = document.createElement("a");
				link.className = "btn btn-secondary transfer-dl";
				link.textContent = "Download";
				link.href = transferDownloadUrl(token, item.id);
				link.setAttribute("download", item.download_name || item.name || "");
				li.appendChild(meta);
				li.appendChild(link);
				list.appendChild(li);
			});
		}
		if (status) {
			status.textContent = items.length === 1 ? "1 item in session" : items.length + " items in session";
		}
	}

	function updateEasyUi(next) {
		var wifi = next.wifi_upload || {};
		var uploadQr = document.getElementById("easy-upload-qr");
		var uploadWait = document.getElementById("easy-upload-wait");
		var transferStatus = document.getElementById("easy-transfer-status");
		var transferFill = document.getElementById("easy-transfer-fill");
		var convertStatus = document.getElementById("easy-convert-status");
		var convertFill = document.getElementById("easy-convert-fill");
		var viewGalleryWrap = document.getElementById("easy-view-gallery-wrap");
		var converted = next.library_counts?.converted || 0;
		var ep = next.extract.progress || { completed: 0, percent: 0 };
		var cp = next.convert.progress || { completed: 0, total: 0, percent: 0 };
		var photoLibraryHint = document.getElementById("photo-library-hint");
		var libDisplay = next.library_root_display || next.library_root;
		var transferPct;
		var issues;
		var errN;
		var invN;
		var parts;
		if (photoLibraryHint && libDisplay) {
			photoLibraryHint.textContent = "Photos and videos are saved under " + libDisplay;
		}
		setQrUrlField("easy-qr-url", wifi.upload_url || "");
		if (wifi.active && uploadQr) {
			uploadQr.hidden = false;
			setQrImageSrc(uploadQr, wifi.qr_url, "easy-upload-qr");
			if (uploadWait) {
				uploadWait.hidden = true;
			}
		} else {
			if (uploadQr) {
				uploadQr.hidden = true;
			}
			if (uploadWait) {
				uploadWait.hidden = false;
				uploadWait.textContent =
					next.extract.phase === "running" || next.extract.phase === "paused"
						? "Preparing upload QR…"
						: "Waiting to start Wi‑Fi receive…";
			}
		}
		if (transferStatus) {
			transferStatus.textContent = easyFileCountLabel(ep.completed, "file received", "files received");
		}
		if (transferFill) {
			transferPct = ep.total > 0 ? ep.percent : ep.completed > 0 ? 100 : 0;
			transferFill.style.width = transferPct + "%";
		}
		if (convertStatus) {
			if (next.convert.phase === "running") {
				convertStatus.textContent = "In progress — " + cp.completed + " / " + cp.total + " (" + cp.percent + "%)";
			} else if (next.convert.phase === "error") {
				convertStatus.textContent = "Failed — " + (next.last_error || "see Advanced for details");
			} else if (next.last_error) {
				convertStatus.textContent = next.last_error;
			} else if (next.convert.phase === "done" && cp.total > 0) {
				convertStatus.textContent = "Completed — " + cp.completed + " file(s)";
			} else if (converted > 0) {
				convertStatus.textContent = easyFileCountLabel(
					converted,
					"file converted, waiting for more",
					"files converted, waiting for more",
				);
			} else {
				convertStatus.textContent = "Waiting for files";
			}
		}
		if (convertFill) {
			convertFill.style.width = (next.convert.phase === "running" ? cp.percent : 0) + "%";
		}
		if (viewGalleryWrap) {
			viewGalleryWrap.classList.toggle("panel-hidden", converted <= 0);
		}
		var importIssues = document.getElementById("easy-import-issues");
		if (importIssues) {
			issues = next.image_import_issues || {};
			errN = issues.errors || 0;
			invN = issues.invalid || 0;
			parts = [];
			if (errN > 0) {
				parts.push(errN + (errN === 1 ? " image failed to convert" : " images failed to convert"));
			}
			if (invN > 0) {
				parts.push(invN + (invN === 1 ? " unsupported image" : " unsupported images"));
			}
			if (parts.length) {
				importIssues.textContent = parts.join(" · ");
				importIssues.classList.remove("panel-hidden");
			} else {
				importIssues.textContent = "";
				importIssues.classList.add("panel-hidden");
			}
		}
	}

	function updateAboutMeta(next) {
		var line = document.getElementById("about-app-meta");
		if (!line || !next) {
			return;
		}
		var ver = next.app_version || "";
		var author = next.app_author || "";
		var contact = next.app_contact || "";
		var parts = ["SpaceMaker"];
		if (ver) {
			parts[0] += " " + ver;
		}
		if (author) {
			parts.push(author);
		}
		line.textContent = parts.join(" · ");
		var link = document.getElementById("about-contact-link");
		if (link && contact) {
			link.href = "mailto:" + contact;
			link.textContent = contact;
		}
	}

	function applyState(next) {
		state = next;
		if (isMobileGalleryShell()) {
			return;
		}
		updateAboutMeta(next);
		setUiModeFromState(next);
		maybeShowMissingTools(next);
		syncConnectionButtons(next.connection_method || "wifi");
		var lib = document.getElementById("input-library-root");
		if (lib && document.activeElement !== lib) {
			lib.value = next.library_root || "";
		}
		syncFolderCheckboxes(next.source_folders);
		if ((next.connection_method || "wifi") !== "wifi") {
			updateDeviceStatus(next);
		}
		updateWifiUploadPanel(next);
		updateExtractUi(next);
		updateConvertUi(next);
		updateVisualizeUi(next);
		updateWarnings(next);
		updateEasyUi(next);
		updateReceiveUi(next);
		updateSendUi(next);
		updateTransferUi(next);
		if (next.managed_tools) {
			renderComponentsList(next.managed_tools);
		}
		maybeShowComponentsScreen(next);
		if (toolsBlockMainApp(next)) {
			return;
		}
		syncActiveModuleView(next);
		validateStep1Form(false);
		updateExtractButtons(next);
	}

	function updateExtractUi(next) {
		var status = document.getElementById("extract-status");
		var bar = document.getElementById("extract-progress");
		var fill = document.getElementById("extract-progress-fill");
		var counts = document.getElementById("extract-counts");
		if (!status) {
			return;
		}
		var phase = next.extract.phase;
		var p = next.extract.progress;
		setStatusLine(status, extractPhaseLabel(phase, p, !!next.extract_stopping));
		if (fill) {
			fill.style.width = p.percent + "%";
		}
		if (bar) {
			bar.setAttribute("aria-valuenow", String(p.percent));
		}
		if (counts) {
			if (
				(next.connection_method || "") === "wifi" &&
				(phase === "running" || phase === "paused" || phase === "stopped" || phase === "done")
			) {
				counts.textContent = p.completed + " files received";
			} else {
				counts.textContent = p.completed + " / " + p.total + " files";
			}
		}
		var extractActive = phase === "running" || phase === "paused";
		document
			.querySelectorAll("#folder-picker input, #select-device, #input-library-root, #chip-copy, #chip-move")
			.forEach(function (el) {
				el.disabled = extractActive;
			});
		document.getElementById("btn-conn-wifi").disabled = extractActive;
		document.getElementById("btn-conn-mtp").disabled = extractActive;
		document.getElementById("btn-conn-adb").disabled = extractActive;
		document.getElementById("btn-conn-afc").disabled = extractActive;
		updateWifiUploadPanel(next);
	}

	function extractPhaseLabel(phase, progress, extractStopping) {
		var method = state?.connection_method;
		if (method === "wifi" && phase === "running") {
			return "Receiving uploads…";
		}
		if (method === "wifi" && phase === "paused") {
			return "Paused — not accepting uploads";
		}
		if (extractStopping && phase === "running") {
			return "Stopping — finishing current file…";
		}
		if (phase === "running") {
			return "In progress — " + progress.percent + "%";
		}
		if (phase === "paused") {
			return "Paused — " + progress.percent + "%";
		}
		if (phase === "done") {
			return "Completed — " + progress.completed + " files";
		}
		if (phase === "stopped") {
			return "Stopped — " + progress.completed + " files done";
		}
		if (phase === "error") {
			return "Error";
		}
		return "Ready";
	}

	function extractIsActive(next) {
		var phase = next?.extract ? next.extract.phase : "";
		return phase === "running" || phase === "paused";
	}

	function canStartConvert(next) {
		if (next.can_start_convert) {
			return true;
		}
		var counts = next.library_counts || {};
		return (counts.originals || 0) > 0;
	}

	function updateExtractButtons(next) {
		var controls = next.extract_controls || {};
		var valid = formValidation.ok;
		var extractActive = extractIsActive(next);
		var btnStart = document.getElementById("btn-start-extract");
		var btnPause = document.getElementById("btn-pause-extract");
		var btnResume = document.getElementById("btn-resume-extract");
		var btnStop = document.getElementById("btn-stop-extract");
		if (btnStart) {
			btnStart.hidden = extractActive;
			btnStart.disabled = extractActive || !controls.start || !valid;
		}
		if (btnPause) {
			btnPause.hidden = !controls.pause;
			btnPause.disabled = !controls.pause;
		}
		if (btnResume) {
			btnResume.hidden = !controls.resume;
			btnResume.disabled = !controls.resume;
		}
		if (btnStop) {
			btnStop.hidden = !controls.stop;
			btnStop.disabled = !controls.stop;
		}
	}

	function updateVisualizeUi(next) {
		var card = document.getElementById("step3-card");
		var status = document.getElementById("visualize-status");
		var btn = document.getElementById("btn-open-gallery");
		if (!card || !status) {
			return;
		}
		var viz = next.visualize || {};
		var enabled = !!viz.enabled;
		card.classList.toggle("disabled", !enabled);
		card.classList.toggle("done", enabled && viz.phase === "completed");
		setStatusLine(status, viz.status_text || "Not started");
		if (btn) {
			btn.disabled = !enabled;
		}
	}

	function updateConvertUi(next) {
		var status = document.getElementById("convert-status");
		var fill = document.getElementById("convert-progress-fill");
		var btn = document.getElementById("btn-start-convert");
		var btnStop = document.getElementById("btn-stop-convert");
		var convertControls = next.convert_controls || {};
		if (!status) {
			return;
		}
		var p = next.convert.progress;
		var extractPhase = next.extract.phase;
		var ready = canStartConvert(next);
		var originals = next.library_counts?.originals || 0;
		var bucketErrorCount = next.library_counts?.error || 0;
		var bucketInvalidCount = next.library_counts?.invalid || 0;
		if (next.convert.phase === "running") {
			setStatusLine(status, "In progress — " + p.completed + " / " + p.total + " (" + p.percent + "%)");
		} else if (next.convert.phase === "stopped") {
			setStatusLine(status, "Stopped — " + p.completed + " / " + p.total + " processed");
		} else if (next.convert.phase === "error") {
			setStatusLine(status, "Failed — " + (next.last_error || "Convert stopped unexpectedly."));
		} else if (next.convert.phase === "done" && p.total > 0) {
			if (bucketErrorCount > 0 || bucketInvalidCount > 0) {
				setStatusLine(
					status,
					"Completed with issues — " +
						(next.last_error || bucketErrorCount + " in error/, " + bucketInvalidCount + " in invalid/"),
				);
			} else {
				setStatusLine(status, "Completed — " + p.completed + " file(s) processed");
			}
		} else if ((extractPhase === "running" || extractPhase === "paused") && ready) {
			setStatusLine(
				status,
				"Extract active — " + originals + " file(s) in originals/; Start convert will stop extract and convert them",
			);
		} else if (extractPhase === "running" || extractPhase === "paused") {
			setStatusLine(status, "Waiting — add files to originals/ to convert during extract");
		} else if (extractPhase === "stopped") {
			setStatusLine(status, "Extract stopped — you can convert files already in originals/");
		} else if (!ready) {
			setStatusLine(status, "Add files to originals/ first (" + originals + " found at library root)");
		} else {
			setStatusLine(status, "Ready — " + originals + " file(s) in originals/");
		}
		if (fill) {
			fill.style.width = p.percent + "%";
		}
		if (btn) {
			btn.hidden = next.convert.phase === "running";
			btn.disabled = !ready || next.convert.phase === "running";
		}
		if (btnStop) {
			btnStop.hidden = !convertControls.stop;
			btnStop.disabled = !convertControls.stop;
		}
		if (
			next.last_error &&
			(next.convert.phase === "error" || (next.convert.phase === "done" && bucketErrorCount > 0))
		) {
			showFormBanner(next.last_error);
		}
	}

	function updateWarnings(next) {
		var counts = next.library_counts || {};
		var errBox = document.getElementById("alert-error");
		var invBox = document.getElementById("alert-invalid");
		var errCount = counts.error || 0;
		var invCount = counts.invalid || 0;
		if (errBox) {
			errBox.hidden = errCount <= 0;
			errBox.style.display = errCount <= 0 ? "none" : "";
		}
		if (invBox) {
			invBox.hidden = invCount <= 0;
			invBox.style.display = invCount <= 0 ? "none" : "";
		}
		var errN = document.getElementById("alert-error-count");
		var invN = document.getElementById("alert-invalid-count");
		if (errN) {
			errN.textContent = String(errCount);
		}
		if (invN) {
			invN.textContent = String(invCount);
		}
		var errDetail = document.getElementById("alert-error-detail");
		if (errDetail) {
			if (errCount > 0 && next.last_error) {
				errDetail.hidden = false;
				errDetail.textContent = next.last_error;
			} else {
				errDetail.hidden = true;
				errDetail.textContent = "";
			}
		}
	}

	function loadDevices() {
		var method = selectedConnectionMethod();
		if (method === "wifi") {
			return Promise.resolve([]);
		}
		return api("GET", "/api/devices?connection_method=" + method)
			.then(function (devices) {
				deviceLabels = {};
				devices.forEach(function (d) {
					deviceLabels[d.device_id] = d.label;
				});
				var sel = document.getElementById("select-device");
				if (!sel) {
					return;
				}
				var previous = sel.value;
				sel.innerHTML = "";
				devices.forEach(function (d) {
					var opt = document.createElement("option");
					opt.value = d.device_id;
					opt.textContent = d.label;
					sel.appendChild(opt);
				});
				if (devices.length) {
					if (previous && deviceLabels[previous]) {
						sel.value = previous;
					} else if (state?.device_id && deviceLabels[state.device_id]) {
						sel.value = state.device_id;
					} else {
						sel.value = devices[0].device_id;
					}
					if (!state?.device_id) {
						return pushSettings();
					}
				}
				if (state) {
					updateDeviceStatus(state);
				}
			})
			.catch(function (err) {
				deviceLabels = {};
				var sel = document.getElementById("select-device");
				if (sel) {
					sel.innerHTML = "";
				}
				if (state) {
					updateDeviceStatus(state);
				}
				showFormBanner(err.message || "Could not list devices.");
			});
	}

	function libraryRootForSave() {
		var lib = document.getElementById("input-library-root");
		var path = lib ? lib.value.trim() : "";
		if (!path && state && state.library_root) {
			path = state.library_root;
		}
		if (!path && defaultLibraryRoot) {
			path = defaultLibraryRoot;
		}
		return path;
	}

	function pushSettings() {
		var sel = document.getElementById("select-device");
		var modeCopy = document.getElementById("chip-copy");
		var deviceId = sel ? sel.value : "";
		var body = {
			library_root: libraryRootForSave(),
			ui_mode: uiMode,
			connection_method: selectedConnectionMethod(),
			transfer_mode: modeCopy?.classList.contains("selected") ? "copy" : "move",
			device_id: deviceId,
			device_label: deviceLabels[deviceId] || "",
			source_folders: selectedFolders(),
		};
		return api("PUT", "/api/settings", body)
			.then(function (data) {
				clearFormBanner();
				applyState(data);
				return data;
			})
			.catch(function (err) {
				showFormBanner(err.message || "Could not save settings.");
				throw err;
			});
	}

	function appendThumbCell(grid, item) {
		var cell = document.createElement("button");
		var img = document.createElement("img");
		var badge;
		cell.type = "button";
		cell.className = "thumb thumb-link";
		img.src = "/thumbs/" + encodeURI(item.relative_path);
		img.alt = item.relative_path;
		img.loading = "lazy";
		cell.appendChild(img);
		if (item.kind === "video") {
			badge = document.createElement("span");
			badge.className = "thumb-badge";
			badge.textContent = "Video";
			cell.appendChild(badge);
		}
		cell.addEventListener("click", function () {
			showGalleryItem(item.relative_path);
		});
		grid.appendChild(cell);
	}

	function formatFileSize(bytes) {
		if (!bytes && bytes !== 0) {
			return "—";
		}
		if (bytes < 1024) {
			return bytes + " B";
		}
		if (bytes < 1024 * 1024) {
			return (bytes / 1024).toFixed(1) + " KB";
		}
		return (bytes / (1024 * 1024)).toFixed(1) + " MB";
	}

	function formatDuration(seconds) {
		if (seconds === null || seconds === undefined) {
			return "—";
		}
		var total = Math.round(seconds);
		var mins = Math.floor(total / 60);
		var secs = total % 60;
		if (mins > 0) {
			return mins + "m " + secs + "s";
		}
		return secs + "s";
	}

	function formatCaptured(iso) {
		if (!iso) {
			return "—";
		}
		var d = new Date(iso);
		if (Number.isNaN(d.getTime())) {
			return iso;
		}
		return d.toLocaleString();
	}

	function setGalleryExportProgress(percent, label) {
		var bar = document.getElementById("gallery-export-progress");
		var fill = document.getElementById("gallery-export-fill");
		var labelEl = document.getElementById("gallery-export-label");
		if (labelEl && label) {
			labelEl.textContent = label;
		}
		if (bar) {
			bar.setAttribute("aria-valuenow", String(percent));
		}
		if (fill) {
			fill.style.width = String(percent) + "%";
		}
	}

	function hideGalleryExportAlert() {
		var alertEl = document.getElementById("gallery-export-alert");
		var err = document.getElementById("gallery-export-error");
		if (alertEl) {
			alertEl.hidden = true;
		}
		if (err) {
			err.hidden = true;
			err.textContent = "";
		}
		setGalleryExportProgress(0, "Preparing download…");
	}

	function triggerFileDownload(url) {
		var a = document.createElement("a");
		a.href = url;
		a.rel = "noopener";
		document.body.appendChild(a);
		a.click();
		a.remove();
	}

	function deliverFriendlyExport(downloadUrl) {
		setGalleryExportProgress(100, "Download starting…");
		triggerFileDownload(downloadUrl);
		setTimeout(hideGalleryExportAlert, 1500);
	}

	function applyGalleryExport(exp) {
		var alertEl;
		var err;
		if (!exp || exp.relative_path !== galleryItemPath) {
			return;
		}
		alertEl = document.getElementById("gallery-export-alert");
		err = document.getElementById("gallery-export-error");
		if (alertEl) {
			alertEl.hidden = false;
		}
		if (exp.phase === "error") {
			setGalleryExportProgress(exp.percent || 0, "Export failed");
			if (err) {
				err.hidden = false;
				err.textContent = exp.error || "Export failed.";
			}
			return;
		}
		if (exp.phase === "running") {
			setGalleryExportProgress(exp.percent || 0, "Preparing download…");
			return;
		}
		if (exp.phase === "done") {
			if (exp.download_url) {
				deliverFriendlyExport(exp.download_url);
			} else {
				setTimeout(hideGalleryExportAlert, 1500);
			}
		}
	}

	function startFriendlyExport() {
		var fmt = galleryItemKind === "video" ? "h264_aac" : "jpeg";
		var alertEl = document.getElementById("gallery-export-alert");
		hideGalleryExportAlert();
		setGalleryExportProgress(0, "Preparing download…");
		if (alertEl) {
			alertEl.hidden = false;
		}
		api("POST", "/api/gallery/export", { relative_path: galleryItemPath, format: fmt })
			.then(applyGalleryExport)
			.catch(function (exportErr) {
				applyGalleryExport({
					relative_path: galleryItemPath,
					phase: "error",
					percent: 0,
					error: exportErr.message || "Export failed.",
				});
			});
	}

	function loadGalleryItemDetail(direction) {
		var stage = document.getElementById("gallery-item-stage");
		var title = document.getElementById("gallery-item-title");
		var metaHost = document.getElementById("gallery-item-meta");
		var friendly = document.getElementById("btn-gallery-friendly");
		if (!stage || !galleryItemPath) {
			return;
		}
		hideGalleryExportAlert();
		setStageLoading(stage, direction);
		updateGalleryItemNav();
		api("GET", "/api/gallery/item?path=" + encodeURIComponent(galleryItemPath))
			.then(function (payload) {
				var meta = payload.metadata || {};
				var rows;
				var mp4Ok;
				galleryItemKind = payload.kind === "video" ? "video" : "image";
				if (title) {
					title.textContent = meta.filename || payload.relative_path;
				}
				renderGalleryItemStage(stage, payload, meta);
				if (friendly) {
					if (payload.kind === "video") {
						mp4Ok = state?.video_friendly_export_available;
						friendly.hidden = !mp4Ok;
						friendly.textContent = "Download as MP4";
					} else {
						friendly.hidden = false;
						friendly.textContent = "Download as JPEG";
					}
				}
				if (metaHost) {
					rows = [
						["On disk", payload.absolute_path || "—"],
						["Captured", formatCaptured(meta.captured_at || payload.captured_at)],
						[
							"Camera",
							meta.camera_make || meta.camera_model
								? [meta.camera_make, meta.camera_model].filter(Boolean).join(" · ")
								: "—",
						],
						["Dimensions", meta.width && meta.height ? meta.width + " × " + meta.height : "—"],
						["File size", formatFileSize(meta.file_size_bytes)],
					];
					if (payload.kind === "video") {
						rows.push(["Duration", formatDuration(meta.duration_seconds)]);
					}
					if (meta.gps) {
						rows.push(["Location", meta.gps]);
					}
					metaHost.innerHTML = "";
					rows.forEach(function (row) {
						var dt = document.createElement("dt");
						var dd = document.createElement("dd");
						dt.textContent = row[0];
						dd.textContent = row[1];
						if (row[0] === "On disk") {
							dt.className = "gallery-disk-path";
							dd.className = "gallery-disk-path";
						}
						metaHost.appendChild(dt);
						metaHost.appendChild(dd);
					});
				}
				updateGalleryItemNav();
			})
			.catch(function () {
				setStageMessage(stage, "Could not load this item.");
				updateGalleryItemNav();
			});
	}

	function galleryDateParts(iso) {
		var d = new Date(iso);
		return { year: d.getFullYear(), month: d.getMonth() + 1 };
	}

	function buildGalleryMonthBlockElement(block) {
		var wrap = document.createElement("div");
		var yTitle;
		var mLabel;
		var grid;
		wrap.className = "month-block";
		if (block.showYear) {
			yTitle = document.createElement("h3");
			yTitle.className = "year-title";
			yTitle.textContent = String(block.year);
			wrap.appendChild(yTitle);
		}
		mLabel = document.createElement("p");
		mLabel.className = "month-label";
		mLabel.textContent = monthName(block.month);
		wrap.appendChild(mLabel);
		grid = document.createElement("div");
		grid.className = "thumb-grid";
		block.items.forEach(function (item) {
			appendThumbCell(grid, item);
		});
		wrap.appendChild(grid);
		return wrap;
	}

	function appendGalleryTimelineItems(items) {
		var host = document.getElementById("timeline-view");
		var sentinel = document.getElementById("gallery-scroll-sentinel");
		if (!host) {
			return;
		}
		items.forEach(function (item) {
			var parts = galleryDateParts(item.captured_at);
			var lastBlock = galleryMonthBlocks[galleryMonthBlocks.length - 1];
			if (!lastBlock || lastBlock.year !== parts.year || lastBlock.month !== parts.month) {
				lastBlock = {
					year: parts.year,
					month: parts.month,
					showYear: !lastBlock || lastBlock.year !== parts.year,
					items: [],
					el: null,
					placeholderEl: null,
					mounted: true,
				};
				galleryMonthBlocks.push(lastBlock);
				lastBlock.el = buildGalleryMonthBlockElement(lastBlock);
				host.insertBefore(lastBlock.el, sentinel);
			}
			lastBlock.items.push(item);
			if (lastBlock.mounted) {
				appendThumbCell(lastBlock.el.querySelector(".thumb-grid"), item);
				galleryMountedTileCount += 1;
			}
		});
	}

	function unmountGalleryMonthBlock(block) {
		var height = block.el.getBoundingClientRect().height;
		var placeholder = document.createElement("div");
		placeholder.className = "month-placeholder";
		placeholder.style.height = height + "px";
		block.el.replaceWith(placeholder);
		block.placeholderEl = placeholder;
		block.el = null;
		block.mounted = false;
		galleryMountedTileCount -= block.items.length;
	}

	function remountGalleryMonthBlock(block) {
		var built = buildGalleryMonthBlockElement(block);
		block.placeholderEl.replaceWith(built);
		block.el = built;
		block.placeholderEl = null;
		block.mounted = true;
		galleryMountedTileCount += block.items.length;
	}

	function enforceGalleryWindow() {
		if (!galleryMonthBlocks.length || !window.innerHeight) {
			return;
		}
		var buffer = window.innerHeight * GALLERY_VIEWPORT_BUFFER_MULTIPLIER;
		var i;
		var block;
		var rect;
		for (i = 0; i < galleryMonthBlocks.length && galleryMountedTileCount > GALLERY_TILE_BUDGET; i += 1) {
			block = galleryMonthBlocks[i];
			if (!block.mounted) {
				continue;
			}
			rect = block.el.getBoundingClientRect();
			if (rect.bottom < -buffer) {
				unmountGalleryMonthBlock(block);
			} else {
				break;
			}
		}
		for (i = 0; i < galleryMonthBlocks.length; i += 1) {
			block = galleryMonthBlocks[i];
			if (block.mounted) {
				continue;
			}
			rect = block.placeholderEl.getBoundingClientRect();
			if (rect.bottom >= -buffer && rect.top <= window.innerHeight + buffer) {
				remountGalleryMonthBlock(block);
			}
		}
	}

	function scheduleGalleryWindowCheck() {
		if (galleryWindowCheckScheduled) {
			return;
		}
		galleryWindowCheckScheduled = true;
		window.requestAnimationFrame(function () {
			galleryWindowCheckScheduled = false;
			enforceGalleryWindow();
		});
	}

	function ensureGalleryWindowListeners() {
		if (galleryWindowListenersBound) {
			return;
		}
		galleryWindowListenersBound = true;
		window.addEventListener("scroll", scheduleGalleryWindowCheck, { passive: true });
		window.addEventListener("resize", scheduleGalleryWindowCheck);
	}

	function setGalleryLoadingMoreVisible(visible) {
		var el = document.getElementById("gallery-loading-more");
		if (el) {
			el.hidden = !visible;
		}
	}

	function hideGallerySentinel() {
		var el = document.getElementById("gallery-scroll-sentinel");
		if (el) {
			el.hidden = true;
		}
		if (galleryIntersectionObserver) {
			galleryIntersectionObserver.disconnect();
		}
	}

	function ensureGallerySentinel() {
		var host = document.getElementById("timeline-view");
		var loading;
		var sentinel;
		if (!host) {
			return;
		}
		loading = document.createElement("p");
		loading.className = "status-line gallery-loading-more";
		loading.id = "gallery-loading-more";
		loading.hidden = true;
		loading.innerHTML = '<span class="gallery-loading-spinner" aria-hidden="true"></span> Loading more…';
		sentinel = document.createElement("div");
		sentinel.id = "gallery-scroll-sentinel";
		host.appendChild(loading);
		host.appendChild(sentinel);
	}

	function setupGalleryIntersectionObserver() {
		var sentinel = document.getElementById("gallery-scroll-sentinel");
		if (!sentinel || typeof IntersectionObserver === "undefined") {
			return;
		}
		if (galleryIntersectionObserver) {
			galleryIntersectionObserver.disconnect();
		}
		galleryIntersectionObserver = new IntersectionObserver(
			function (entries) {
				entries.forEach(function (entry) {
					if (entry.isIntersecting && galleryHasMore && !galleryLoadingMore) {
						fetchGalleryTimelinePage();
					}
				});
			},
			{ rootMargin: "600px 0px" },
		);
		galleryIntersectionObserver.observe(sentinel);
	}

	function showGalleryTimelineMessage(message) {
		var host = document.getElementById("timeline-view");
		if (host) {
			host.innerHTML = '<p class="status-line">' + message + "</p>";
		}
	}

	function fetchGalleryTimelinePage() {
		var isFirstPage = galleryMonthBlocks.length === 0;
		var url = "/api/gallery/timeline?limit=" + GALLERY_PAGE_LIMIT;
		if (galleryLoadingMore) {
			return;
		}
		if (galleryNextCursor) {
			url += "&cursor=" + encodeURIComponent(galleryNextCursor);
		}
		galleryLoadingMore = true;
		setGalleryLoadingMoreVisible(true);
		api("GET", url)
			.then(function (payload) {
				var items = payload.items || [];
				galleryLoadingMore = false;
				setGalleryLoadingMoreVisible(false);
				galleryNextCursor = payload.next_cursor || null;
				galleryHasMore = Boolean(galleryNextCursor);
				if (isFirstPage && !items.length) {
					showGalleryTimelineMessage("No media in converted/ yet.");
					galleryHasMore = false;
					return;
				}
				appendGalleryTimelineItems(items);
				if (!galleryHasMore) {
					hideGallerySentinel();
				}
				scheduleGalleryWindowCheck();
			})
			.catch(function () {
				galleryLoadingMore = false;
				setGalleryLoadingMoreVisible(false);
				galleryHasMore = false;
				hideGallerySentinel();
				if (isFirstPage) {
					showGalleryTimelineMessage("Could not load gallery.");
				}
			});
	}

	function loadGallery() {
		var host = document.getElementById("timeline-view");
		if (!host) {
			return;
		}
		if (galleryIntersectionObserver) {
			galleryIntersectionObserver.disconnect();
			galleryIntersectionObserver = null;
		}
		galleryMonthBlocks = [];
		galleryNextCursor = null;
		galleryHasMore = true;
		galleryLoadingMore = false;
		galleryMountedTileCount = 0;
		host.innerHTML = "";
		ensureGallerySentinel();
		ensureGalleryWindowListeners();
		setupGalleryIntersectionObserver();
		fetchGalleryTimelinePage();
	}

	function daysInMonth(year, month) {
		return new Date(year, month, 0).getDate();
	}

	function shiftCalendarMonth(delta) {
		calendarMonth += delta;
		if (calendarMonth > 12) {
			calendarMonth = 1;
			calendarYear += 1;
		} else if (calendarMonth < 1) {
			calendarMonth = 12;
			calendarYear -= 1;
		}
		calendarSelectedDay = null;
		loadCalendarMonth();
	}

	function renderCalendarGrid(daysWithMedia) {
		var grid = document.getElementById("calendar-grid");
		var title = document.getElementById("calendar-title");
		var firstDow;
		var lead;
		var i;
		var blank;
		var total;
		var mediaSet = {};
		var day;
		var cell;
		if (!grid || !title) {
			return;
		}
		title.textContent = monthName(calendarMonth) + " " + calendarYear;
		grid.innerHTML = "";
		["M", "T", "W", "T", "F", "S", "S"].forEach(function (label) {
			var wd = document.createElement("span");
			wd.className = "cal-cell weekday";
			wd.textContent = label;
			grid.appendChild(wd);
		});
		firstDow = new Date(calendarYear, calendarMonth - 1, 1).getDay();
		lead = (firstDow + 6) % 7;
		for (i = 0; i < lead; i += 1) {
			blank = document.createElement("span");
			blank.className = "cal-cell";
			grid.appendChild(blank);
		}
		total = daysInMonth(calendarYear, calendarMonth);
		daysWithMedia.forEach(function (d) {
			mediaSet[d] = true;
		});
		for (day = 1; day <= total; day += 1) {
			if (mediaSet[day]) {
				cell = document.createElement("button");
				cell.type = "button";
				cell.className = "cal-cell has-media";
				if (calendarSelectedDay === day) {
					cell.classList.add("selected");
				}
				cell.textContent = String(day);
				cell.addEventListener(
					"click",
					(function (d) {
						return function () {
							selectCalendarDay(d);
						};
					})(day),
				);
			} else {
				cell = document.createElement("span");
				cell.className = "cal-cell";
				cell.textContent = String(day);
			}
			grid.appendChild(cell);
		}
	}

	function selectCalendarDay(day) {
		calendarSelectedDay = day;
		loadCalendarMonth();
		api("GET", "/api/gallery/day?year=" + calendarYear + "&month=" + calendarMonth + "&day=" + day)
			.then(function (payload) {
				var label = document.getElementById("calendar-day-label");
				var thumbs = document.getElementById("calendar-day-thumbs");
				if (!label || !thumbs) {
					return;
				}
				label.hidden = false;
				label.textContent = monthName(calendarMonth) + " " + day + ", " + calendarYear;
				thumbs.innerHTML = "";
				if (!payload.items?.length) {
					thumbs.innerHTML = '<p class="status-line">No items for this day.</p>';
					return;
				}
				payload.items.forEach(function (item) {
					appendThumbCell(thumbs, item);
				});
			})
			.catch(function () {
				var thumbs = document.getElementById("calendar-day-thumbs");
				if (thumbs) {
					thumbs.innerHTML = '<p class="status-line">Could not load day.</p>';
				}
			});
	}

	function loadCalendarMonth() {
		api("GET", "/api/gallery/calendar?year=" + calendarYear + "&month=" + calendarMonth)
			.then(function (payload) {
				var label;
				var thumbs;
				renderCalendarGrid(payload.days_with_media || []);
				if (calendarSelectedDay === null) {
					label = document.getElementById("calendar-day-label");
					thumbs = document.getElementById("calendar-day-thumbs");
					if (label) {
						label.hidden = true;
					}
					if (thumbs) {
						thumbs.innerHTML = "";
					}
				}
			})
			.catch(function () {
				var grid = document.getElementById("calendar-grid");
				if (grid) {
					grid.innerHTML = '<p class="status-line">Could not load calendar.</p>';
				}
			});
	}

	function setGalleryQrPlaceholder(placeholderEl, qrUrl) {
		var img;
		if (!placeholderEl) {
			return;
		}
		placeholderEl.innerHTML = "";
		img = document.createElement("img");
		img.src = qrUrl || "/api/gallery/qr.svg";
		img.alt = "QR code for gallery URL";
		placeholderEl.appendChild(img);
	}

	function applyGalleryFirewallHints(info, hintEl, fwWarnEl) {
		var showHint;
		var fw;
		if (hintEl) {
			showHint = info.lan_reachable === false;
			hintEl.hidden = !showHint;
		}
		fw = info.firewall || {};
		if (fwWarnEl) {
			if (fw.port_open === false && fw.message) {
				fwWarnEl.textContent = fw.message;
				fwWarnEl.hidden = false;
			} else if (fw.port_open === null && fw.message && info.lan_reachable) {
				fwWarnEl.textContent = fw.message;
				fwWarnEl.hidden = false;
			} else {
				fwWarnEl.hidden = true;
				fwWarnEl.textContent = "";
			}
		}
	}

	function loadServerInfo() {
		api("GET", "/api/server-info").then(function (info) {
			var qr = document.getElementById("qr-placeholder");
			var urlField = document.getElementById("gallery-url");
			var popupUrl = document.getElementById("gallery-popup-url");
			var portLabel = document.getElementById("gallery-lan-port");
			var portText;
			var galleryUrl = info.gallery_url || "";
			setGalleryQrPlaceholder(qr, info.qr_url);
			setGalleryQrPlaceholder(document.getElementById("gallery-popup-qr"), info.qr_url);
			if (urlField) {
				urlField.textContent = galleryUrl;
			}
			if (popupUrl) {
				popupUrl.textContent = galleryUrl;
			}
			portText = info.port ? String(info.port) : "8765";
			if (portLabel) {
				portLabel.textContent = portText;
			}
			document.querySelectorAll(".lan-firewall-port").forEach(function (el) {
				el.textContent = portText;
			});
			applyGalleryFirewallHints(
				info,
				document.getElementById("gallery-lan-hint"),
				document.getElementById("gallery-firewall-warn"),
			);
			applyGalleryFirewallHints(
				info,
				document.getElementById("gallery-popup-lan-hint"),
				document.getElementById("gallery-popup-firewall-warn"),
			);
		});
	}

	function isGalleryEntryPath() {
		return location.pathname === "/gallery" || location.pathname.indexOf("/gallery/item/") === 0;
	}

	function connectWs() {
		var proto = location.protocol === "https:" ? "wss" : "ws";
		var ws = new WebSocket(proto + "://" + location.host + "/ws");
		ws.onmessage = function (ev) {
			var msg = JSON.parse(ev.data);
			if (msg.type === "state") {
				applyState(msg.state);
			}
			if (msg.type === "gallery_export") {
				applyGalleryExport(msg.export);
			}
		};
		ws.onclose = function () {
			setTimeout(connectWs, 2000);
		};
	}

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
				loadCalendarMonth();
			});
		}
		onClick("btn-cal-prev", function () {
			shiftCalendarMonth(-1);
		});
		onClick("btn-cal-next", function () {
			shiftCalendarMonth(1);
		});
		onClick("btn-gallery-item-back", function () {
			showView("gallery");
		});
		onClick("btn-gallery-item-prev", function () {
			shiftGalleryItem(-1);
		});
		onClick("btn-gallery-item-next", function () {
			shiftGalleryItem(1);
		});
		onClick("btn-gallery-download", function () {
			if (!galleryItemPath) {
				return;
			}
			triggerFileDownload("/media/" + encodeURI(galleryItemPath) + "?download=1");
		});
		onClick("btn-gallery-open", function () {
			if (!galleryItemPath) {
				return;
			}
			api("POST", "/api/gallery/open", { relative_path: galleryItemPath, target: "file" }).catch(function (err) {
				window.alert(err.message || "Could not open this file.");
			});
		});
		onClick("btn-gallery-open-folder", function () {
			if (!galleryItemPath) {
				return;
			}
			api("POST", "/api/gallery/open", { relative_path: galleryItemPath, target: "folder" }).catch(function (err) {
				window.alert(err.message || "Could not open the folder.");
			});
		});
		onClick("btn-gallery-friendly", function () {
			if (!galleryItemPath) {
				return;
			}
			startFriendlyExport();
		});
		onClick("btn-gallery-delete", function () {
			if (!galleryItemPath) {
				return;
			}
			if (!window.confirm("Delete this file from converted/ on this computer? This cannot be undone.")) {
				return;
			}
			api("DELETE", "/api/gallery/item?path=" + encodeURIComponent(galleryItemPath))
				.then(function () {
					galleryItemPath = "";
					showView("gallery");
				})
				.catch(function (err) {
					window.alert(err.message || "Could not delete this file.");
				});
		});
	}

	function bootstrapMobileGalleryShell() {
		bindGalleryUi();
		routeFromPath();
		connectWs();
	}

	function bootstrapDesktopShell() {
		document.querySelectorAll(".view-tabs button").forEach(function (btn) {
			btn.addEventListener("click", function () {
				var v = btn.getAttribute("data-view");
				if (v === "home") {
					goHomeHub();
					return;
				}
				showView(v);
			});
		});

		document.querySelectorAll("[data-module]").forEach(function (tile) {
			tile.addEventListener("click", function () {
				var moduleId = tile.getAttribute("data-module");
				if (moduleId) {
					enterModule(moduleId);
				}
			});
		});
		document.querySelectorAll(".breadcrumb-home").forEach(function (btn) {
			btn.addEventListener("click", function () {
				goHomeHub();
			});
		});
		onClick("btn-open-documents-folder", function () {
			api("POST", "/api/documents/open-folder").catch(function (err) {
				showFormBanner(err.message || "Could not open documents folder.");
			});
		});

		function mergeShareSelection(extra) {
			var base = state?.share_selection ? state.share_selection.slice() : [];
			var seen = {};
			var merged = [];
			var i;
			var _p;
			var key;
			function addPath(path) {
				if (!path || !String(path).trim()) {
					return;
				}
				key = String(path).trim();
				if (seen[key]) {
					return;
				}
				seen[key] = true;
				merged.push(key);
			}
			for (i = 0; i < base.length; i++) {
				addPath(base[i]);
			}
			if (extra) {
				if (Array.isArray(extra)) {
					for (i = 0; i < extra.length; i++) {
						addPath(extra[i]);
					}
				} else {
					addPath(extra);
				}
			}
			return merged;
		}

		function refreshShareSelection(paths) {
			return api("POST", "/api/share/selection", { paths: paths })
				.then(applyState)
				.catch(function (err) {
					if (paths?.length) {
						window.alert(err.message || "Could not update the share list.");
					} else {
						showFormBanner(err.message || "Could not update the share list.");
					}
					throw err;
				});
		}

		onClick("btn-share-clear", function () {
			refreshShareSelection([]);
		});
		onClick("btn-share-add-files", function () {
			if (!window.pywebview?.api?.choose_files) {
				showFormBanner("Use the desktop app to pick files.");
				return;
			}
			var current = state?.share_selection?.[0] || "";
			Promise.resolve(window.pywebview.api.choose_files(current))
				.then(function (picked) {
					if (!picked?.length) {
						return null;
					}
					return refreshShareSelection(mergeShareSelection(picked));
				})
				.catch(function () {
					showFormBanner("Could not open the file picker.");
				});
		});
		onClick("btn-share-add-folder", function () {
			if (!window.pywebview?.api?.choose_share_folder) {
				showFormBanner("Use the desktop app to pick a folder.");
				return;
			}
			var current = state?.share_selection?.[state.share_selection.length - 1] || "";
			Promise.resolve(window.pywebview.api.choose_share_folder(current))
				.then(function (folder) {
					if (!folder || !String(folder).trim()) {
						return null;
					}
					var countPromise = window.pywebview.api.share_folder_file_count
						? Promise.resolve(window.pywebview.api.share_folder_file_count(folder))
						: Promise.resolve(1);
					return countPromise.then(function (count) {
						if (count < 1) {
							window.alert("This folder has no files. Choose a folder that contains at least one file.");
							return null;
						}
						var merged = mergeShareSelection(folder);
						if (state?.share_selection && merged.length === state.share_selection.length) {
							return null;
						}
						return refreshShareSelection(merged);
					});
				})
				.catch(function () {
					showFormBanner("Could not open the folder picker.");
				});
		});

		function addTransferPaths(paths) {
			if (!paths?.length) {
				return Promise.resolve(null);
			}
			return api("POST", "/api/transfer/add", { paths: paths })
				.then(applyState)
				.catch(function (err) {
					window.alert(err.message || "Could not add to the transfer session.");
					throw err;
				});
		}

		onClick("btn-transfer-add-files", function () {
			if (!window.pywebview?.api?.choose_files) {
				showFormBanner("Use the desktop app to pick files.");
				return;
			}
			Promise.resolve(window.pywebview.api.choose_files(""))
				.then(function (picked) {
					if (!picked?.length) {
						return null;
					}
					return addTransferPaths(picked);
				})
				.catch(function () {
					showFormBanner("Could not open the file picker.");
				});
		});
		onClick("btn-transfer-add-folder", function () {
			if (!window.pywebview?.api?.choose_share_folder) {
				showFormBanner("Use the desktop app to pick a folder.");
				return;
			}
			Promise.resolve(window.pywebview.api.choose_share_folder(""))
				.then(function (folder) {
					if (!folder || !String(folder).trim()) {
						return null;
					}
					var countPromise = window.pywebview.api.share_folder_file_count
						? Promise.resolve(window.pywebview.api.share_folder_file_count(folder))
						: Promise.resolve(1);
					return countPromise.then(function (count) {
						if (count < 1) {
							window.alert("This folder has no files. Choose a folder that contains at least one file.");
							return null;
						}
						return addTransferPaths([folder]);
					});
				})
				.catch(function () {
					showFormBanner("Could not open the folder picker.");
				});
		});

		function rememberMainViewBeforeFooterPage() {
			var active = document.querySelector(".screen.active");
			if (
				active &&
				(active.id === "view-home" ||
					active.id === "view-easy" ||
					active.id === "view-wizard" ||
					active.id === "view-receive-files" ||
					active.id === "view-send-files" ||
					active.id === "view-transfer-files" ||
					active.id === "view-gallery" ||
					active.id === "view-gallery-item")
			) {
				lastMainView = active.id === "view-gallery-item" || active.id === "view-gallery" ? "gallery" : "home";
			}
		}

		document.getElementById("btn-footer-settings").addEventListener("click", function () {
			rememberMainViewBeforeFooterPage();
			if (state?.managed_tools) {
				renderComponentsList(state.managed_tools);
			}
			showView("settings");
		});
		document.getElementById("btn-footer-legal").addEventListener("click", function () {
			rememberMainViewBeforeFooterPage();
			showView("legal");
		});
		document.getElementById("btn-settings-back").addEventListener("click", function () {
			if (state && toolsBlockMainApp(state)) {
				showView("components", { skipHistory: true });
				return;
			}
			showView(lastMainView === "gallery" ? "gallery" : "home");
		});
		document.getElementById("btn-legal-back").addEventListener("click", function () {
			showView(lastMainView === "gallery" ? "gallery" : "home");
		});
		onClick("btn-components-continue", function () {
			api("POST", "/api/tools/components-continue")
				.then(function (payload) {
					sessionStorage.setItem(COMPONENTS_DISMISS_KEY, "1");
					renderComponentsList(payload);
					return api("GET", "/api/settings");
				})
				.then(applyState)
				.then(function () {
					showView("home");
					return null;
				})
				.catch(function (err) {
					showFormBanner(err.message || "Could not continue setup.");
				});
		});
		onClick("btn-components-retry", function () {
			runComponentsEnsure().catch(function (err) {
				showFormBanner(err.message || "Could not retry downloads.");
			});
		});
		onClick("btn-settings-delete-tools", function () {
			if (!window.confirm("Delete all downloaded components? System packages will not be removed.")) {
				return;
			}
			api("DELETE", "/api/tools/downloaded")
				.then(function (payload) {
					sessionStorage.removeItem(COMPONENTS_DISMISS_KEY);
					renderComponentsList(payload);
					return api("GET", "/api/settings");
				})
				.then(applyState)
				.then(function () {
					if (state && toolsBlockMainApp(state)) {
						showView("components", { skipHistory: true });
					}
				})
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Could not delete downloaded components.");
				});
		});
		onClick("btn-settings-retry-downloads", function () {
			runComponentsEnsure().catch(function (err) {
				showFormBanner(err.message || "Could not retry downloads.");
			});
		});

		bindGalleryUi();

		document.getElementById("btn-lan-firewall-info").addEventListener("click", function () {
			var panel = document.getElementById("lan-firewall-info-panel");
			var open = panel.classList.toggle("visible");
			panel.setAttribute("aria-hidden", open ? "false" : "true");
			this.setAttribute("aria-expanded", open ? "true" : "false");
		});

		document.getElementById("btn-connection-info").addEventListener("click", function () {
			var panel = document.getElementById("connection-info-panel");
			var open = panel.classList.toggle("visible");
			panel.setAttribute("aria-hidden", open ? "false" : "true");
			this.setAttribute("aria-expanded", open ? "true" : "false");
		});
		bindInfoPanelToggle("btn-easy-qr-info", "easy-qr-info-panel");
		bindInfoPanelToggle("btn-receive-qr-info", "receive-qr-info-panel");
		bindInfoPanelToggle("btn-send-qr-info", "send-qr-info-panel");
		bindInfoPanelToggle("btn-transfer-qr-info", "transfer-qr-info-panel");
		bindInfoPanelToggle("btn-wifi-qr-info", "wifi-qr-info-panel");

		function switchConnectionMethod(method) {
			syncConnectionButtons(method);
			deviceLabels = {};
			var sel = document.getElementById("select-device");
			if (sel) {
				sel.innerHTML = "";
			}
			if (method === "wifi") {
				validateStep1Form(true);
				return pushSettings();
			}
			return loadDevices().then(function () {
				return pushSettings();
			});
		}

		document.getElementById("btn-conn-wifi").addEventListener("click", function () {
			switchConnectionMethod("wifi");
		});
		document.getElementById("btn-conn-mtp").addEventListener("click", function () {
			switchConnectionMethod("mtp");
		});
		document.getElementById("btn-conn-adb").addEventListener("click", function () {
			switchConnectionMethod("adb");
		});
		document.getElementById("btn-conn-afc").addEventListener("click", function () {
			switchConnectionMethod("afc");
		});

		var chipCopy = document.getElementById("chip-copy");
		var chipMove = document.getElementById("chip-move");
		chipCopy.addEventListener("click", function () {
			if (selectedConnectionMethod() === "wifi") {
				return;
			}
			chipCopy.classList.add("selected");
			chipMove.classList.remove("selected");
			pushSettings();
		});
		chipMove.addEventListener("click", function () {
			if (chipMove.disabled) {
				return;
			}
			chipMove.classList.add("selected");
			chipCopy.classList.remove("selected");
			pushSettings();
		});

		var libraryInput = document.getElementById("input-library-root");
		libraryInput.addEventListener("input", function () {
			validateStep1Form(true);
			if (state) {
				updateExtractButtons(state);
			}
		});
		libraryInput.addEventListener("change", function () {
			validateStep1Form(true);
			pushSettings();
		});
		document.getElementById("select-device").addEventListener("change", function () {
			validateStep1Form(true);
			pushSettings();
		});
		document.getElementById("btn-browse-library").addEventListener("click", function () {
			var lib = document.getElementById("input-library-root");
			var current = lib ? lib.value.trim() : "";
			if (window.pywebview?.api?.choose_library_folder) {
				Promise.resolve(window.pywebview.api.choose_library_folder(current))
					.then(function (path) {
						if (path && lib) {
							lib.value = path;
							validateStep1Form(true);
							return pushSettings();
						}
						return null;
					})
					.catch(function () {
						showFormBanner("Could not open the folder picker.");
					});
				return;
			}
			showFormBanner("Browse works in the desktop app. Type an absolute path, or run uv run task spacemaker.");
			if (lib) {
				lib.focus();
			}
		});
		document.querySelectorAll("#folder-picker input").forEach(function (box) {
			box.addEventListener("change", pushSettings);
		});

		document.getElementById("btn-start-extract").addEventListener("click", function () {
			if (!validateStep1Form(true).ok) {
				showFormBanner("Fix the highlighted fields before starting extract.");
				return;
			}
			var btnStart = document.getElementById("btn-start-extract");
			if (btnStart) {
				btnStart.hidden = true;
				btnStart.disabled = true;
			}
			pushSettings()
				.then(function () {
					return api("POST", "/api/extract/start");
				})
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Extract could not start.");
					if (state) {
						updateExtractButtons(state);
					}
				});
		});
		document.getElementById("btn-pause-extract").addEventListener("click", function () {
			if (!state?.extract_controls?.pause) {
				return;
			}
			api("POST", "/api/extract/pause")
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Pause failed.");
				});
		});
		document.getElementById("btn-resume-extract").addEventListener("click", function () {
			if (!state?.extract_controls?.resume) {
				return;
			}
			api("POST", "/api/extract/resume")
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Resume failed.");
				});
		});
		document.getElementById("btn-stop-extract").addEventListener("click", function () {
			if (!state?.extract_controls?.stop) {
				return;
			}
			api("POST", "/api/extract/stop")
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Stop failed.");
				});
		});
		document.getElementById("btn-stop-convert").addEventListener("click", function () {
			if (!state?.convert_controls?.stop) {
				return;
			}
			api("POST", "/api/convert/stop")
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Stop convert failed.");
				});
		});
		document.getElementById("btn-start-convert").addEventListener("click", function () {
			if (!canStartConvert(state || {})) {
				showFormBanner("Convert is not ready yet — check library path and originals/ folder.");
				return;
			}
			var sync = extractIsActive(state || {}) ? Promise.resolve(state) : pushSettings();
			sync
				.then(function () {
					return api("POST", "/api/convert/start");
				})
				.then(applyState)
				.catch(function (err) {
					showFormBanner(err.message || "Convert could not start.");
				});
		});
		document.getElementById("btn-move-errors").addEventListener("click", function () {
			api("POST", "/api/error/move-to-converted")
				.then(function () {
					return api("GET", "/api/settings");
				})
				.then(applyState);
		});
		onClick("btn-open-gallery", function () {
			showView("gallery");
		});
		onClick("btn-easy-view-gallery", function () {
			showView("gallery");
		});
		onClick("btn-gallery-phone-help", function (ev) {
			ev.stopPropagation();
			toggleGalleryPhonePopup();
		});
		onClick("btn-gallery-phone-popup-close", function () {
			closeGalleryPhonePopup();
		});
		document.addEventListener("click", function (ev) {
			var popup = document.getElementById("gallery-phone-popup");
			var fab = document.getElementById("btn-gallery-phone-help");
			if (!popup || popup.classList.contains("panel-hidden")) {
				return;
			}
			if (popup.contains(ev.target) || fab?.contains(ev.target)) {
				return;
			}
			closeGalleryPhonePopup();
		});

		api("GET", "/api/defaults")
			.then(function (defaults) {
				defaultLibraryRoot = defaults.default_library_root || "";
				var lib = document.getElementById("input-library-root");
				if (lib) {
					lib.placeholder = defaultLibraryRoot;
				}
				return api("GET", "/api/settings");
			})
			.then(function (settings) {
				if (!settings.library_root && defaultLibraryRoot) {
					settings.library_root = defaultLibraryRoot;
					return api("PUT", "/api/settings", {
						library_root: defaultLibraryRoot,
						ui_mode: settings.ui_mode || "easy",
						connection_method: settings.connection_method,
						transfer_mode: settings.transfer_mode,
						device_id: settings.device_id,
						device_label: settings.device_label,
						source_folders: settings.source_folders || ["dcim", "pictures", "movies"],
					});
				}
				return settings;
			})
			.then(applyState)
			.then(function () {
				warnIfStaleShell(state);
				if (state && toolsBlockMainApp(state)) {
					maybeShowComponentsScreen(state);
					return runComponentsEnsure()
						.then(function () {
							return api("GET", "/api/settings");
						})
						.then(applyState);
				}
				return null;
			})
			.then(function () {
				if (state && toolsBlockMainApp(state)) {
					maybeShowComponentsScreen(state);
					return null;
				}
				routeFromPath();
				if (isGalleryEntryPath()) {
					return null;
				}
				if (state?.active_module && state.active_module !== "home") {
					showView(moduleToViewId(state.active_module), { skipHistory: true });
				} else {
					showView("home", { skipHistory: true });
				}
				if (state && state.active_module === "usb_photo_backup" && selectedConnectionMethod() !== "wifi") {
					return loadDevices();
				}
				return null;
			})
			.then(function () {
				if (isGalleryEntryPath()) {
					return null;
				}
				validateStep1Form(true);
				if (state) {
					updateExtractButtons(state);
				}
			})
			.then(loadServerInfo)
			.catch(function (err) {
				showFormBanner(err.message || "Failed to load settings.");
			});
		connectWs();
	}

	if (isMobileGalleryShell()) {
		bootstrapMobileGalleryShell();
	} else {
		bootstrapDesktopShell();
	}
})();
