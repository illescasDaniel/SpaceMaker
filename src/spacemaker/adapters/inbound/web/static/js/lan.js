// @ts-nocheck — typed surface: types.ts/state.ts/api.ts/dom.ts
import { R, S } from "./state.js";

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
		transferStatus.textContent = R.easyFileCountLabel(rp.completed, "file received", "files received");
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
	R.setQrUrlField("receive-qr-url", session.page_url || "");
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
		R.setQrUrlField("send-qr-url", share.page_url || "");
	} else if (qrSection && uploadQr) {
		qrSection.classList.add("panel-hidden");
		uploadQr.hidden = true;
		R.setQrUrlField("send-qr-url", "");
	}
}
function showTransferSaveTip(displayPath) {
	var tip = document.getElementById("transfer-save-tip");
	var tipText = document.getElementById("transfer-save-tip-text");
	var actions = document.getElementById("transfer-save-actions");
	if (tipText) {
		tipText.textContent = "Saved to " + (displayPath || "Documents/SpaceMaker");
	}
	if (tip) {
		tip.hidden = false;
	}
	if (actions) {
		actions.hidden = false;
	}
}
function hideTransferSaveTip() {
	var tip = document.getElementById("transfer-save-tip");
	var tipText = document.getElementById("transfer-save-tip-text");
	var actions = document.getElementById("transfer-save-actions");
	if (tip) {
		tip.hidden = true;
	}
	if (tipText) {
		tipText.textContent = "";
	}
	if (actions) {
		actions.hidden = true;
	}
}
function saveTransferItemToDocuments(fileId) {
	return R.api("POST", "/api/transfer/save", { file_id: fileId })
		.then(function (result) {
			showTransferSaveTip(result.saved_path_display || result.saved_path || "");
		})
		.catch(function (err) {
			window.alert(err.message || "Could not save to Documents/SpaceMaker.");
		});
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
	var pageUrl = session.page_url || "";
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
		hideTransferSaveTip();
	}
	R.setQrUrlField("transfer-qr-url", pageUrl);
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
			var btn = document.createElement("button");
			btn.type = "button";
			btn.className = "btn btn-secondary transfer-dl";
			btn.textContent = "Download";
			btn.addEventListener("click", function () {
				saveTransferItemToDocuments(item.id);
			});
			li.appendChild(meta);
			li.appendChild(btn);
			list.appendChild(li);
		});
	}
	if (status) {
		status.textContent = items.length === 1 ? "1 item in session" : items.length + " items in session";
	}
}
function bindLanDesktop() {
	function mergeShareSelection(extra) {
		var base = S.state?.share_selection ? S.state.share_selection.slice() : [];
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
		return R.api("POST", "/api/share/selection", { paths: paths })
			.then(applyState)
			.catch(function (err) {
				if (paths?.length) {
					window.alert(err.message || "Could not update the share list.");
				} else {
					R.showFormBanner(err.message || "Could not update the share list.");
				}
				throw err;
			});
	}
	R.onClick("btn-share-clear", function () {
		refreshShareSelection([]);
	});
	R.onClick("btn-share-add-files", function () {
		if (!window.pywebview?.api?.choose_files) {
			R.showFormBanner("Use the desktop app to pick files.");
			return;
		}
		var current = S.state?.share_selection?.[0] || "";
		Promise.resolve(window.pywebview.api.choose_files(current))
			.then(function (picked) {
				if (!picked?.length) {
					return null;
				}
				return refreshShareSelection(mergeShareSelection(picked));
			})
			.catch(function () {
				R.showFormBanner("Could not open the file picker.");
			});
	});
	R.onClick("btn-share-add-folder", function () {
		if (!window.pywebview?.api?.choose_share_folder) {
			R.showFormBanner("Use the desktop app to pick a folder.");
			return;
		}
		var current = S.state?.share_selection?.[S.state.share_selection.length - 1] || "";
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
					if (S.state?.share_selection && merged.length === S.state.share_selection.length) {
						return null;
					}
					return refreshShareSelection(merged);
				});
			})
			.catch(function () {
				R.showFormBanner("Could not open the folder picker.");
			});
	});
	function addTransferPaths(paths) {
		if (!paths?.length) {
			return Promise.resolve(null);
		}
		return R.api("POST", "/api/transfer/add", { paths: paths })
			.then(applyState)
			.catch(function (err) {
				window.alert(err.message || "Could not add to the transfer session.");
				throw err;
			});
	}
	R.onClick("btn-transfer-add-files", function () {
		if (!window.pywebview?.api?.choose_files) {
			R.showFormBanner("Use the desktop app to pick files.");
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
				R.showFormBanner("Could not open the file picker.");
			});
	});
	R.onClick("btn-transfer-add-folder", function () {
		if (!window.pywebview?.api?.choose_share_folder) {
			R.showFormBanner("Use the desktop app to pick a folder.");
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
				R.showFormBanner("Could not open the folder picker.");
			});
	});
}
R.updateReceiveUi = updateReceiveUi;
R.updateSendUi = updateSendUi;
R.showTransferSaveTip = showTransferSaveTip;
R.hideTransferSaveTip = hideTransferSaveTip;
R.saveTransferItemToDocuments = saveTransferItemToDocuments;
R.updateTransferUi = updateTransferUi;
R.bindLanDesktop = bindLanDesktop;

export {
	bindLanDesktop,
	hideTransferSaveTip,
	saveTransferItemToDocuments,
	showTransferSaveTip,
	updateReceiveUi,
	updateSendUi,
	updateTransferUi,
};
