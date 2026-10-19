/** `Remove`-able list of picker extras, shared by USB file transfer and the photo-backup wizard. */

function extraPathKind(path: string): string {
	const name = path.split("/").pop() || path;
	return name.indexOf(".") > 0 ? "file" : "folder";
}

function renderExtraSources(
	listId: string,
	paths: string[] | undefined,
	onRemove: (remaining: string[]) => void,
): void {
	const list = document.getElementById(listId);
	if (!list) {
		return;
	}
	list.textContent = "";
	const items = paths ?? [];
	list.hidden = items.length === 0;
	for (const path of items) {
		const li = document.createElement("li");
		li.setAttribute("data-extra-path", path);
		const name = document.createElement("span");
		name.className = "uft-extra-name";
		name.textContent = path;
		const kind = document.createElement("span");
		kind.className = "uft-extra-kind";
		kind.textContent = extraPathKind(path);
		const remove = document.createElement("button");
		remove.type = "button";
		remove.className = "btn-uft-extra-remove";
		remove.textContent = "Remove";
		remove.setAttribute("aria-label", "Remove " + path);
		remove.addEventListener("click", () => {
			onRemove(items.filter((p) => p !== path));
		});
		li.appendChild(name);
		li.appendChild(kind);
		li.appendChild(remove);
		list.appendChild(li);
	}
}

export { extraPathKind, renderExtraSources };
