/** Pure helpers for Components setup chrome (poll gate + Details expand). */
export const COMPONENTS_POLL_MS = 3000;
export function shouldRunComponentsPoll(viewId) {
	return viewId === "view-components";
}
export function detailsExpandedForSummary(summaryStatus) {
	return (summaryStatus || "missing") !== "ok";
}
