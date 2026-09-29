import { apiSend } from "./api.js";
import { errorMessage, onClick, setQrUrlField, showFormBanner } from "./dom.js";
import { applyState, easyFileCountLabel } from "./shell.js";
import { S } from "./state.js";

function updateReceiveUi(next) {
	const session = next.receive_files_session;
	const uploadQr = document.getElementById("receive-upload-qr");
	const uploadWait = document.getElementById("receive-upload-wait");
	const transferStatus = document.getElementById("receive-transfer-status");
	const transferFill = document.getElementById("receive-transfer-fill");
	const destHint = document.getElementById("receive-dest-hint");
	const rp = next.receive_files?.progress ?? { completed: 0, percent: 0, total: 0 };
	if (session?.active && uploadQr instanceof HTMLImageElement) {
		uploadQr.hidden = false;
		if (session.qr_url) {
			uploadQr.src = session.qr_url + "&_=" + Date.now();
		}
		if (uploadWait) {
			uploadWait.hidden = true;
		}
	} else if (uploadQr instanceof HTMLImageElement) {
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
		const transferPct = rp.total > 0 ? rp.percent : rp.completed > 0 ? 100 : 0;
		transferFill.style.width = transferPct + "%";
	}
	const destDisplay = next.documents_receive_root_display || next.documents_receive_root;
	if (destHint && destDisplay) {
		destHint.textContent = "Files are saved under " + destDisplay;
	}
	const openWrap = document.getElementById("receive-open-wrap");
	if (openWrap) {
		const fileCount =
			typeof next.documents_receive_file_count === "number" ? next.documents_receive_file_count : rp.completed;
		openWrap.classList.toggle("panel-hidden", fileCount < 1);
	}
	setQrUrlField("receive-qr-url", session?.page_url || "");
}
function updateSendUi(next) {
	const share = next.file_share;
	const paths = next.share_selection || [];
	const list = document.getElementById("share-path-list");
	const qrSection = document.getElementById("send-qr-section");
	const uploadQr = document.getElementById("send-share-qr");
	const serverHint = document.getElementById("send-server-only-hint");
	const hasDesktop = !!window.pywebview?.api;
	if (serverHint) {
		serverHint.classList.toggle("panel-hidden", hasDesktop);
	}
	if (list) {
		list.innerHTML = "";
		paths.forEach((p) => {
			const li = document.createElement("li");
			li.textContent = p;
			list.appendChild(li);
		});
	}
	if (share?.active && paths.length && qrSection && uploadQr instanceof HTMLImageElement) {
		qrSection.classList.remove("panel-hidden");
		uploadQr.hidden = false;
		if (share.qr_url) {
			uploadQr.src = share.qr_url + "&_=" + Date.now();
		}
		setQrUrlField("send-qr-url", share.page_url || "");
	} else if (qrSection && uploadQr instanceof HTMLImageElement) {
		qrSection.classList.add("panel-hidden");
		uploadQr.hidden = true;
		setQrUrlField("send-qr-url", "");
	}
}
function showTransferSaveTip(displayPath) {
	const tip = document.getElementById("transfer-save-tip");
	const tipText = document.getElementById("transfer-save-tip-text");
	const actions = document.getElementById("transfer-save-actions");
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
	const tip = document.getElementById("transfer-save-tip");
	const tipText = document.getElementById("transfer-save-tip-text");
	const actions = document.getElementById("transfer-save-actions");
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
	return apiSend("POST", "/api/transfer/save", { file_id: fileId })
		.then((result) => {
			showTransferSaveTip(result.saved_path_display || result.saved_path || "");
		})
		.catch((err) => {
			window.alert(errorMessage(err, "Could not save to Documents/SpaceMaker."));
		});
}
function updateTransferUi(next) {
	const session = next.transfer_files_session;
	const uploadQr = document.getElementById("transfer-qr");
	const uploadWait = document.getElementById("transfer-qr-wait");
	const list = document.getElementById("transfer-item-list");
	const status = document.getElementById("transfer-item-status");
	const serverHint = document.getElementById("transfer-server-only-hint");
	const hasDesktop = !!window.pywebview?.api;
	const items = session?.items || [];
	const pageUrl = session?.page_url || "";
	if (serverHint) {
		serverHint.classList.toggle("panel-hidden", hasDesktop);
	}
	if (session?.active && uploadQr instanceof HTMLImageElement) {
		uploadQr.hidden = false;
		if (session.qr_url) {
			uploadQr.src = session.qr_url + "&_=" + Date.now();
		}
		if (uploadWait) {
			uploadWait.hidden = true;
		}
	} else if (uploadQr instanceof HTMLImageElement) {
		uploadQr.hidden = true;
		if (uploadWait) {
			uploadWait.hidden = false;
			uploadWait.textContent = "Waiting to start transfer session…";
		}
		hideTransferSaveTip();
	}
	setQrUrlField("transfer-qr-url", pageUrl);
	if (list) {
		list.innerHTML = "";
		items.forEach((item) => {
			const li = document.createElement("li");
			li.className = "transfer-item";
			const meta = document.createElement("span");
			meta.className = "transfer-item-meta";
			const name = document.createElement("span");
			name.className = "transfer-item-name";
			name.textContent = item.name || "";
			const from = document.createElement("span");
			from.className = "transfer-item-from";
			from.textContent =
				(item.kind === "folder_zip" ? "folder · " : "") +
				"from " +
				(item.origin_label || (item.origin === "pc" ? "PC" : "Phone"));
			meta.appendChild(name);
			meta.appendChild(from);
			const btn = document.createElement("button");
			btn.type = "button";
			btn.className = "btn btn-secondary transfer-dl";
			btn.textContent = "Download";
			btn.addEventListener("click", () => {
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
		const base = S.state?.share_selection ? S.state.share_selection.slice() : [];
		const seen = {};
		const merged = [];
		function addPath(path) {
			if (!path || !String(path).trim()) {
				return;
			}
			const key = String(path).trim();
			if (seen[key]) {
				return;
			}
			seen[key] = true;
			merged.push(key);
		}
		base.forEach(addPath);
		if (extra) {
			if (Array.isArray(extra)) {
				extra.forEach(addPath);
			} else {
				addPath(extra);
			}
		}
		return merged;
	}
	function refreshShareSelection(paths) {
		return apiSend("POST", "/api/share/selection", { paths: paths })
			.then((data) => {
				applyState(data);
				return data;
			})
			.catch((err) => {
				if (paths.length) {
					window.alert(errorMessage(err, "Could not update the share list."));
				} else {
					showFormBanner(errorMessage(err, "Could not update the share list."));
				}
				throw err;
			});
	}
	onClick("btn-share-clear", () => {
		refreshShareSelection([]);
	});
	onClick("btn-share-add-files", () => {
		if (!window.pywebview?.api?.choose_files) {
			showFormBanner("Use the desktop app to pick files.");
			return;
		}
		const current = S.state?.share_selection?.[0] || "";
		Promise.resolve(window.pywebview.api.choose_files(current))
			.then((picked) => {
				if (!picked?.length) {
					return null;
				}
				return refreshShareSelection(mergeShareSelection(picked));
			})
			.catch(() => {
				showFormBanner("Could not open the file picker.");
			});
	});
	onClick("btn-share-add-folder", () => {
		if (!window.pywebview?.api?.choose_share_folder) {
			showFormBanner("Use the desktop app to pick a folder.");
			return;
		}
		const shareSelection = S.state?.share_selection;
		const current = shareSelection?.[shareSelection.length - 1] || "";
		Promise.resolve(window.pywebview.api.choose_share_folder(current))
			.then((folder) => {
				if (!folder || !String(folder).trim()) {
					return null;
				}
				const countPromise = window.pywebview?.api?.share_folder_file_count
					? Promise.resolve(window.pywebview.api.share_folder_file_count(folder))
					: Promise.resolve(1);
				return countPromise.then((count) => {
					if (count < 1) {
						window.alert("This folder has no files. Choose a folder that contains at least one file.");
						return null;
					}
					const merged = mergeShareSelection(folder);
					if (S.state?.share_selection && merged.length === S.state.share_selection.length) {
						return null;
					}
					return refreshShareSelection(merged);
				});
			})
			.catch(() => {
				showFormBanner("Could not open the folder picker.");
			});
	});
	function addTransferPaths(paths) {
		if (!paths?.length) {
			return Promise.resolve(null);
		}
		return apiSend("POST", "/api/transfer/add", { paths: paths })
			.then((data) => {
				applyState(data);
				return data;
			})
			.catch((err) => {
				window.alert(errorMessage(err, "Could not add to the transfer session."));
				throw err;
			});
	}
	onClick("btn-transfer-add-files", () => {
		if (!window.pywebview?.api?.choose_files) {
			showFormBanner("Use the desktop app to pick files.");
			return;
		}
		Promise.resolve(window.pywebview.api.choose_files(""))
			.then((picked) => {
				if (!picked?.length) {
					return null;
				}
				return addTransferPaths(picked);
			})
			.catch(() => {
				showFormBanner("Could not open the file picker.");
			});
	});
	onClick("btn-transfer-add-folder", () => {
		if (!window.pywebview?.api?.choose_share_folder) {
			showFormBanner("Use the desktop app to pick a folder.");
			return;
		}
		Promise.resolve(window.pywebview.api.choose_share_folder(""))
			.then((folder) => {
				if (!folder || !String(folder).trim()) {
					return null;
				}
				const countPromise = window.pywebview?.api?.share_folder_file_count
					? Promise.resolve(window.pywebview.api.share_folder_file_count(folder))
					: Promise.resolve(1);
				return countPromise.then((count) => {
					if (count < 1) {
						window.alert("This folder has no files. Choose a folder that contains at least one file.");
						return null;
					}
					return addTransferPaths([folder]);
				});
			})
			.catch(() => {
				showFormBanner("Could not open the folder picker.");
			});
	});
}

export {
	bindLanDesktop,
	hideTransferSaveTip,
	saveTransferItemToDocuments,
	showTransferSaveTip,
	updateReceiveUi,
	updateSendUi,
	updateTransferUi,
};
