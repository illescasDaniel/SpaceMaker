/** Pure helpers for Components setup chrome (poll gate + Details expand). */

export const COMPONENTS_POLL_MS = 3000;

export function shouldRunComponentsPoll(viewId: string): boolean {
	return viewId === "view-components";
}

export function detailsExpandedForSummary(summaryStatus: string | undefined | null): boolean {
	return (summaryStatus || "missing") !== "ok";
}
