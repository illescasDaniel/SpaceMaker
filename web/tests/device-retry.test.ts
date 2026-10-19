import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
	DEVICE_RETRY_INTERVAL_MS,
	DEVICE_RETRY_MAX,
	type DeviceListOutcome,
	startDeviceRetry,
} from "../src/device-retry.ts";

function given(outcomes: DeviceListOutcome[]) {
	const queue = outcomes.slice();
	const list = vi.fn(() => Promise.resolve(queue.shift() ?? "empty"));
	const onSearching = vi.fn();
	const onGiveUp = vi.fn();
	return { list, onSearching, onGiveUp, options: { list, onSearching, onGiveUp } };
}

async function tick(times = 1): Promise<void> {
	for (let i = 0; i < times; i++) {
		await vi.advanceTimersByTimeAsync(DEVICE_RETRY_INTERVAL_MS);
	}
}

describe("startDeviceRetry", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});
	afterEach(() => {
		vi.useRealTimers();
	});

	it("uses a 3 s interval and 5 retries", () => {
		expect(DEVICE_RETRY_INTERVAL_MS).toBe(3000);
		expect(DEVICE_RETRY_MAX).toBe(5);
	});

	it("does not list before the first interval elapses", async () => {
		const t = given(["found"]);
		startDeviceRetry(t.options);
		await vi.advanceTimersByTimeAsync(DEVICE_RETRY_INTERVAL_MS - 1);
		expect(t.list).not.toHaveBeenCalled();
	});

	it("announces searching with the attempt number, then stops once a device is found", async () => {
		const t = given(["empty", "found"]);
		startDeviceRetry(t.options);
		await tick(1);
		expect(t.onSearching).toHaveBeenNthCalledWith(1, 1);
		await tick(1);
		expect(t.onSearching).toHaveBeenNthCalledWith(2, 2);
		expect(t.list).toHaveBeenCalledTimes(2);
		await tick(5);
		expect(t.list).toHaveBeenCalledTimes(2);
		expect(t.onGiveUp).not.toHaveBeenCalled();
	});

	it("gives up after the retry budget when nothing is found", async () => {
		const t = given([]);
		startDeviceRetry(t.options);
		await tick(DEVICE_RETRY_MAX);
		expect(t.list).toHaveBeenCalledTimes(DEVICE_RETRY_MAX);
		expect(t.onGiveUp).toHaveBeenCalledTimes(1);
		await tick(5);
		expect(t.list).toHaveBeenCalledTimes(DEVICE_RETRY_MAX);
		expect(t.onGiveUp).toHaveBeenCalledTimes(1);
	});

	it("stops without giving up when a retry errors", async () => {
		const t = given(["error"]);
		startDeviceRetry(t.options);
		await tick(5);
		expect(t.list).toHaveBeenCalledTimes(1);
		expect(t.onGiveUp).not.toHaveBeenCalled();
	});

	it("stops and restores the status when the run becomes inactive", async () => {
		const t = given([]);
		let active = true;
		startDeviceRetry({ ...t.options, isActive: () => active });
		await tick(1);
		active = false;
		await tick(5);
		expect(t.list).toHaveBeenCalledTimes(1);
		expect(t.onSearching).toHaveBeenCalledTimes(1);
		expect(t.onGiveUp).toHaveBeenCalledTimes(1);
	});

	it("stops when cancelled, and cancel is idempotent", async () => {
		const t = given([]);
		const run = startDeviceRetry(t.options);
		await tick(1);
		run.cancel();
		run.cancel();
		await tick(5);
		expect(t.list).toHaveBeenCalledTimes(1);
		expect(t.onGiveUp).not.toHaveBeenCalled();
	});

	it("ignores a listing that resolves after cancel", async () => {
		let resolve: (o: DeviceListOutcome) => void = () => undefined;
		const list = vi.fn(() => new Promise<DeviceListOutcome>((r) => (resolve = r)));
		const onSearching = vi.fn();
		const onGiveUp = vi.fn();
		const run = startDeviceRetry({ list, onSearching, onGiveUp });
		await tick(1);
		run.cancel();
		resolve("empty");
		await tick(10);
		expect(list).toHaveBeenCalledTimes(1);
		expect(onGiveUp).not.toHaveBeenCalled();
	});

	it("never has two listings in flight", async () => {
		let inFlight = 0;
		let peak = 0;
		const list = vi.fn(async (): Promise<DeviceListOutcome> => {
			inFlight++;
			peak = Math.max(peak, inFlight);
			await new Promise((r) => setTimeout(r, DEVICE_RETRY_INTERVAL_MS * 2));
			inFlight--;
			return "empty";
		});
		startDeviceRetry({ list, onSearching: vi.fn(), onGiveUp: vi.fn() });
		await tick(30);
		expect(peak).toBe(1);
	});

	it("a new run after cancel starts a fresh budget", async () => {
		const first = given([]);
		const run = startDeviceRetry(first.options);
		await tick(3);
		run.cancel();
		const second = given([]);
		startDeviceRetry(second.options);
		await tick(DEVICE_RETRY_MAX);
		expect(second.list).toHaveBeenCalledTimes(DEVICE_RETRY_MAX);
		expect(second.onGiveUp).toHaveBeenCalledTimes(1);
	});
});
