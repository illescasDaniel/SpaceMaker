(function () {
	var lastMainView = "wizard";
	var state = null;
	var deviceLabels = {};
	var defaultLibraryRoot = "";
	var formValidation = { ok: false, library: "", device: "", folders: "" };
	var calendarYear = new Date().getFullYear();
	var calendarMonth = new Date().getMonth() + 1;
	var calendarSelectedDay = null;

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

	function validateStep1Form(showFieldErrors) {
		var lib = document.getElementById("input-library-root");
		var sel = document.getElementById("select-device");
		var libraryPath = lib ? lib.value.trim() : "";
		var folders = selectedFolders();
		var deviceOk = !!(sel && sel.value);
		var libraryOk = isAbsolutePath(libraryPath);
		var foldersOk = folders.length > 0;
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

	function pathForMainView(viewId) {
		if (viewId === "gallery") {
			return "/gallery";
		}
		if (viewId === "wizard") {
			return "/";
		}
		return null;
	}

	function showView(viewId, options) {
		var path;
		options = options || {};
		document.querySelectorAll(".screen").forEach(function (s) {
			s.classList.remove("active");
		});
		document.getElementById("view-" + viewId).classList.add("active");
		if (viewId === "wizard" || viewId === "gallery") {
			document.querySelectorAll(".view-tabs button").forEach(function (b) {
				b.classList.toggle("active", b.getAttribute("data-view") === viewId);
			});
			lastMainView = viewId;
			if (viewId === "gallery") {
				loadGallery();
			}
			if (!options.skipHistory) {
				path = pathForMainView(viewId);
				if (path !== null && location.pathname !== path) {
					history.pushState({ view: viewId }, "", path);
				}
			}
		}
	}

	function routeFromPath() {
		if (location.pathname === "/gallery") {
			showView("gallery", { skipHistory: true });
			return;
		}
		if (location.pathname === "/" || location.pathname === "") {
			showView("wizard", { skipHistory: true });
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
		return method === "adb" ? "ADB" : "MTP";
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
		showFormBanner("Bundled tools missing (" + missing.join(", ") + "). Run: uv run task dev-tools -- --from-path");
	}

	function applyState(next) {
		state = next;
		maybeShowMissingTools(next);
		var lib = document.getElementById("input-library-root");
		if (lib && document.activeElement !== lib) {
			lib.value = next.library_root || "";
		}
		syncFolderCheckboxes(next.source_folders);
		updateDeviceStatus(next);
		updateExtractUi(next);
		updateConvertUi(next);
		updateVisualizeUi(next);
		updateWarnings(next);
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
		status.innerHTML = "<strong>Status:</strong> " + extractPhaseLabel(phase, p);
		if (fill) {
			fill.style.width = p.percent + "%";
		}
		if (bar) {
			bar.setAttribute("aria-valuenow", String(p.percent));
		}
		if (counts) {
			counts.textContent = p.completed + " / " + p.total + " files";
		}
		var extractActive = phase === "running" || phase === "paused";
		document
			.querySelectorAll("#folder-picker input, #select-device, #input-library-root, #chip-copy, #chip-move")
			.forEach(function (el) {
				el.disabled = extractActive;
			});
		document.getElementById("btn-conn-mtp").disabled = extractActive;
		document.getElementById("btn-conn-adb").disabled = extractActive;
	}

	function extractPhaseLabel(phase, progress) {
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
		var phase = next && next.extract ? next.extract.phase : "";
		return phase === "running" || phase === "paused";
	}

	function canStartConvert(next) {
		if (extractIsActive(next)) {
			return false;
		}
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
		status.innerHTML = "<strong>Status:</strong> " + (viz.status_text || "Not started");
		if (btn) {
			btn.disabled = !enabled;
		}
	}

	function updateConvertUi(next) {
		var status = document.getElementById("convert-status");
		var fill = document.getElementById("convert-progress-fill");
		var btn = document.getElementById("btn-start-convert");
		if (!status) {
			return;
		}
		var p = next.convert.progress;
		var extractPhase = next.extract.phase;
		var ready = canStartConvert(next);
		var originals = (next.library_counts || {}).originals || 0;
		var bucketErrorCount = (next.library_counts || {}).error || 0;
		var bucketInvalidCount = (next.library_counts || {}).invalid || 0;
		if (next.convert.phase === "running") {
			status.innerHTML =
				"<strong>Status:</strong> In progress — " + p.completed + " / " + p.total + " (" + p.percent + "%)";
		} else if (next.convert.phase === "error") {
			status.innerHTML = "<strong>Status:</strong> Failed — " + (next.last_error || "Convert stopped unexpectedly.");
		} else if (next.convert.phase === "done" && p.total > 0) {
			if (bucketErrorCount > 0 || bucketInvalidCount > 0) {
				status.innerHTML =
					"<strong>Status:</strong> Completed with issues — " +
					(next.last_error || bucketErrorCount + " in error/, " + bucketInvalidCount + " in invalid/");
			} else {
				status.innerHTML = "<strong>Status:</strong> Completed — " + p.completed + " file(s) processed";
			}
		} else if (extractPhase === "running" || extractPhase === "paused") {
			status.innerHTML = "<strong>Status:</strong> Waiting — extract in progress (Step 1)";
		} else if (extractPhase === "stopped") {
			status.innerHTML = "<strong>Status:</strong> Extract stopped — you can convert files already in originals/";
		} else if (!ready) {
			status.innerHTML =
				"<strong>Status:</strong> Add files to originals/ first (" + originals + " found at library root)";
		} else {
			status.innerHTML = "<strong>Status:</strong> Ready — " + originals + " file(s) in originals/";
		}
		if (fill) {
			fill.style.width = p.percent + "%";
		}
		if (btn) {
			btn.disabled = !ready || next.convert.phase === "running";
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
		var method = document.getElementById("btn-conn-adb").classList.contains("active") ? "adb" : "mtp";
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
			connection_method: document.getElementById("btn-conn-adb").classList.contains("active") ? "adb" : "mtp",
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
		var cell = document.createElement("div");
		var img = document.createElement("img");
		var badge;
		cell.className = "thumb";
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
		grid.appendChild(cell);
	}

	function loadGallery() {
		api("GET", "/api/gallery/timeline")
			.then(function (groups) {
				var host = document.getElementById("timeline-view");
				var currentYear = null;
				var yearBlock = null;
				var yTitle;
				if (!host) {
					return;
				}
				host.innerHTML = "";
				if (!groups.length) {
					host.innerHTML = '<p class="status-line">No media in converted/ yet.</p>';
					return;
				}
				groups.forEach(function (g) {
					if (g.year !== currentYear) {
						currentYear = g.year;
						yearBlock = document.createElement("div");
						yearBlock.className = "year-block";
						yTitle = document.createElement("h3");
						yTitle.className = "year-title";
						yTitle.textContent = String(g.year);
						yearBlock.appendChild(yTitle);
						host.appendChild(yearBlock);
					}
					var mLabel = document.createElement("p");
					mLabel.className = "month-label";
					mLabel.textContent = monthName(g.month);
					yearBlock.appendChild(mLabel);
					var grid = document.createElement("div");
					grid.className = "thumb-grid";
					g.items.forEach(function (item) {
						appendThumbCell(grid, item);
					});
					yearBlock.appendChild(grid);
				});
			})
			.catch(function () {
				var host = document.getElementById("timeline-view");
				if (host) {
					host.innerHTML = '<p class="status-line">Could not load gallery.</p>';
				}
			});
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
				if (!payload.items || !payload.items.length) {
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

	function loadServerInfo() {
		api("GET", "/api/server-info").then(function (info) {
			var qr = document.getElementById("qr-placeholder");
			var urlField = document.getElementById("gallery-url");
			var hint = document.getElementById("gallery-lan-hint");
			var portLabel = document.getElementById("gallery-lan-port");
			var fwWarn = document.getElementById("gallery-firewall-warn");
			var showHint;
			var img;
			var fw;
			var portText;
			if (qr) {
				qr.innerHTML = "";
				img = document.createElement("img");
				img.src = info.qr_url || "/api/gallery/qr.svg";
				img.alt = "QR code for gallery URL";
				qr.appendChild(img);
			}
			if (urlField) {
				urlField.textContent = info.gallery_url;
			}
			portText = info.port ? String(info.port) : "8765";
			if (portLabel) {
				portLabel.textContent = portText;
			}
			document.querySelectorAll(".lan-firewall-port").forEach(function (el) {
				el.textContent = portText;
			});
			if (hint) {
				showHint = info.lan_reachable === false;
				hint.hidden = !showHint;
			}
			fw = info.firewall || {};
			if (fwWarn) {
				if (fw.port_open === false && fw.message) {
					fwWarn.textContent = fw.message;
					fwWarn.hidden = false;
				} else if (fw.port_open === null && fw.message && info.lan_reachable) {
					fwWarn.textContent = fw.message;
					fwWarn.hidden = false;
				} else {
					fwWarn.hidden = true;
					fwWarn.textContent = "";
				}
			}
		});
	}

	function isGalleryEntryPath() {
		return location.pathname === "/gallery";
	}

	function connectWs() {
		var proto = location.protocol === "https:" ? "wss" : "ws";
		var ws = new WebSocket(proto + "://" + location.host + "/ws");
		ws.onmessage = function (ev) {
			var msg = JSON.parse(ev.data);
			if (msg.type === "state") {
				applyState(msg.state);
			}
		};
		ws.onclose = function () {
			setTimeout(connectWs, 2000);
		};
	}

	document.querySelectorAll(".view-tabs button").forEach(function (btn) {
		btn.addEventListener("click", function () {
			showView(btn.getAttribute("data-view"));
		});
	});

	document.getElementById("btn-footer-legal").addEventListener("click", function () {
		var active = document.querySelector(".screen.active");
		if (active && (active.id === "view-wizard" || active.id === "view-gallery")) {
			lastMainView = active.id.replace("view-", "");
		}
		showView("legal");
	});
	document.getElementById("btn-legal-back").addEventListener("click", function () {
		showView(lastMainView);
	});

	var btnTimeline = document.getElementById("btn-timeline");
	var btnCalendar = document.getElementById("btn-calendar");
	var timelineView = document.getElementById("timeline-view");
	var calendarView = document.getElementById("calendar-view");
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
	document.getElementById("btn-cal-prev").addEventListener("click", function () {
		shiftCalendarMonth(-1);
	});
	document.getElementById("btn-cal-next").addEventListener("click", function () {
		shiftCalendarMonth(1);
	});

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

	function switchConnectionMethod(method) {
		var isAdb = method === "adb";
		document.getElementById("btn-conn-mtp").classList.toggle("active", !isAdb);
		document.getElementById("btn-conn-adb").classList.toggle("active", isAdb);
		deviceLabels = {};
		var sel = document.getElementById("select-device");
		if (sel) {
			sel.innerHTML = "";
		}
		return loadDevices().then(function () {
			return pushSettings();
		});
	}

	document.getElementById("btn-conn-mtp").addEventListener("click", function () {
		switchConnectionMethod("mtp");
	});
	document.getElementById("btn-conn-adb").addEventListener("click", function () {
		switchConnectionMethod("adb");
	});

	var chipCopy = document.getElementById("chip-copy");
	var chipMove = document.getElementById("chip-move");
	chipCopy.addEventListener("click", function () {
		chipCopy.classList.add("selected");
		chipMove.classList.remove("selected");
		pushSettings();
	});
	chipMove.addEventListener("click", function () {
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
		if (window.pywebview && window.pywebview.api && window.pywebview.api.choose_library_folder) {
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
		if (!state || !state.extract_controls || !state.extract_controls.pause) {
			return;
		}
		api("POST", "/api/extract/pause")
			.then(applyState)
			.catch(function (err) {
				showFormBanner(err.message || "Pause failed.");
			});
	});
	document.getElementById("btn-resume-extract").addEventListener("click", function () {
		if (!state || !state.extract_controls || !state.extract_controls.resume) {
			return;
		}
		api("POST", "/api/extract/resume")
			.then(applyState)
			.catch(function (err) {
				showFormBanner(err.message || "Resume failed.");
			});
	});
	document.getElementById("btn-stop-extract").addEventListener("click", function () {
		if (!state || !state.extract_controls || !state.extract_controls.stop) {
			return;
		}
		api("POST", "/api/extract/stop")
			.then(applyState)
			.catch(function (err) {
				showFormBanner(err.message || "Stop failed.");
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
	document.getElementById("btn-open-gallery").addEventListener("click", function () {
		showView("gallery");
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
			routeFromPath();
			if (isGalleryEntryPath()) {
				return null;
			}
			return loadDevices();
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
})();
