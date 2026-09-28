import { R } from "./state.js";
import type { HttpMethod, JsonValue } from "./types.js";

export async function apiSend(method: HttpMethod | string, path: string, body?: unknown): Promise<JsonValue> {
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
		throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
	}
	return data as JsonValue;
}

export async function apiGet(path: string): Promise<JsonValue> {
	return apiSend("GET", path);
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

R.apiSend = (url, method, body) => apiSend(method || "GET", url, body);
R.apiGet = apiGet;
R.formatApiError = formatApiError;
