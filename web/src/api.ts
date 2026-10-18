import type { HttpMethod, JsonValue } from "./types.ts";

/** Non-2xx API response: `status` is the HTTP status and `detail` the raw FastAPI `detail`
 * (a string, or an object such as `{code: "cpu_confirm_required", video_count: 2}`). */
export class ApiError extends Error {
	readonly status: number;
	readonly detail: unknown;

	constructor(message: string, status: number, detail: unknown) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.detail = detail;
	}
}

/** Generic response type defaults to the loose `JsonValue` the server actually promises
 * (every route here returns `dict[str, object]`); callers that know a payload's shape
 * pass it explicitly, e.g. `apiSend<GalleryItemDetail>("GET", ...)`. */
export async function apiSend<T = JsonValue>(method: HttpMethod, path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = { Accept: "application/json" };
	const init: RequestInit = { method, headers };
	if (body !== undefined) {
		headers["Content-Type"] = "application/json";
		init.body = JSON.stringify(body);
	}
	const response = await fetch(path, init);
	const data: unknown = await response.json().catch(() => ({}));
	if (!response.ok) {
		const detail =
			typeof data === "object" && data !== null && "detail" in data
				? (data as { detail: unknown }).detail
				: response.statusText;
		throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), response.status, detail);
	}
	return data as T;
}

export async function apiGet<T = JsonValue>(path: string): Promise<T> {
	return apiSend<T>("GET", path);
}

export function formatApiError(item: unknown): string {
	if (typeof item === "string") {
		return item;
	}
	if (typeof item === "object" && item !== null && "msg" in item) {
		const msg = (item as { msg: unknown }).msg;
		if (typeof msg === "string") {
			return msg;
		}
	}
	return JSON.stringify(item);
}
