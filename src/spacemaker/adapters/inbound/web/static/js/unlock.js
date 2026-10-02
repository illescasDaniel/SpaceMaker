/** Phone unlock page (served in place of any page while the network passcode is set). */
export function bindUnlock(env) {
	const { doc, fetchFn, loc, hist } = env;
	const msg = doc.getElementById("msg");
	const input = doc.getElementById("passcode");
	const btn = doc.getElementById("btn-unlock");
	const form = doc.getElementById("unlock-form");
	if (!msg || !(input instanceof HTMLInputElement) || !(btn instanceof HTMLButtonElement) || !form) {
		return;
	}
	let timer;
	function show(kind, text) {
		if (msg) {
			msg.className = kind ? `msg ${kind}` : "msg";
			msg.textContent = text;
		}
	}
	function setDisabled(disabled) {
		if (input instanceof HTMLInputElement && btn instanceof HTMLButtonElement) {
			input.disabled = disabled;
			btn.disabled = disabled;
		}
	}
	function lock(seconds) {
		setDisabled(true);
		clearInterval(timer);
		let left = seconds;
		const tick = () => {
			if (left <= 0) {
				clearInterval(timer);
				setDisabled(false);
				show("", "");
				return;
			}
			show("wait", `Too many attempts. Try again in ${left} seconds.`);
			left -= 1;
		};
		tick();
		timer = setInterval(tick, 1000);
	}
	async function send(payload) {
		const res = await fetchFn("/api/unlock", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		});
		if (res.ok) {
			// Drop the one-time QR token from the address bar, then load the page that was asked for.
			hist.replaceState(null, "", loc.pathname + loc.search);
			loc.reload();
			return;
		}
		const body = await res.json().catch(() => ({}));
		if (res.status === 429) {
			lock(body.retry_after_seconds || 30);
		} else {
			show("error", "Wrong passcode. Try again.");
		}
	}
	function submit(payload) {
		send(payload).catch(() => show("error", "Could not reach SpaceMaker."));
	}
	const key = new URLSearchParams(loc.hash.slice(1)).get("k");
	if (key) {
		submit({ token: key });
	}
	form.addEventListener("submit", (event) => {
		event.preventDefault();
		if (input.value) {
			submit({ passcode: input.value });
		}
	});
}
// Runs on the real page only; the form is absent anywhere else (including unit tests).
if (typeof document !== "undefined" && document.getElementById("unlock-form")) {
	bindUnlock({ doc: document, fetchFn: window.fetch.bind(window), loc: location, hist: history });
}
