/** Phone pages: when the network passcode changes or is cleared mid-session, API calls return
 * 401 "passcode-required"; reload so the server answers with the unlock page. */
export function installAuthGuard(win) {
	const nativeFetch = win.fetch.bind(win);
	win.fetch = async (...args) => {
		const response = await nativeFetch(...args);
		if (response.status === 401) {
			const body = await response
				.clone()
				.json()
				.catch(() => null);
			if (typeof body === "object" && body !== null && "detail" in body && body.detail === "passcode-required") {
				win.location.reload();
			}
		}
		return response;
	};
}
if (typeof window !== "undefined") {
	installAuthGuard(window);
}
