import { beforeEach, describe, expect, it, vi } from "vitest";

import { appendLocation, mapsUrl, parseGps } from "../src/gps.ts";

describe("parseGps", () => {
	it("parses ExifTool DMS text", () => {
		expect(parseGps(`52 deg 31' 12.00" N, 13 deg 24' 18.00" E`)).toEqual({ lat: 52.52, lon: 13.405 });
	});

	it("parses DMS with degree sign and S/W hemispheres as negatives", () => {
		expect(parseGps(`33° 52' 7.68" S, 151° 12' 33.48" W`)).toEqual({ lat: -33.8688, lon: -151.2093 });
	});

	it("parses decimal degrees with hemisphere letters", () => {
		expect(parseGps("52.5200° N, 13.4050° E")).toEqual({ lat: 52.52, lon: 13.405 });
		expect(parseGps("33.5 S, 70.25 W")).toEqual({ lat: -33.5, lon: -70.25 });
	});

	it("parses a signed decimal pair", () => {
		expect(parseGps("-33.8688, 151.2093")).toEqual({ lat: -33.8688, lon: 151.2093 });
	});

	it.each([
		"",
		"—",
		"unknown",
		"52.52",
		`95 deg 0' 0" N, 10 deg 0' 0" E`,
		`10 deg 60' 0" N, 10 deg 0' 0" E`,
		"10, 200",
		"-91, 0",
		`1.0, 2.0"><script>`,
		"1.0, 2.0 and more",
		"NaN, 1",
	])("rejects %j", (text) => {
		expect(parseGps(text)).toBeNull();
	});
});

describe("mapsUrl", () => {
	it("builds a Google Maps search URL with trimmed decimals", () => {
		expect(mapsUrl({ lat: 52.52, lon: 13.405 })).toBe("https://www.google.com/maps/search/?api=1&query=52.52,13.405");
		expect(mapsUrl({ lat: -33.8688, lon: -70 })).toBe("https://www.google.com/maps/search/?api=1&query=-33.8688,-70");
	});

	it("limits to 6 decimal places", () => {
		expect(mapsUrl({ lat: 1.23456789, lon: 2 })).toBe("https://www.google.com/maps/search/?api=1&query=1.234568,2");
	});
});

describe("appendLocation", () => {
	let dd: HTMLElement;

	beforeEach(() => {
		document.body.innerHTML = "<dl><dd id='loc'></dd></dl>";
		dd = document.getElementById("loc") as HTMLElement;
		delete window.pywebview;
	});

	it("renders text plus a safe link for a located item", () => {
		appendLocation(dd, `52 deg 31' 12.00" N, 13 deg 24' 18.00" E`);
		const link = dd.querySelector("a.gallery-open-maps") as HTMLAnchorElement;
		expect(dd.className).toContain("gallery-meta-location");
		expect(dd.querySelector("span")?.textContent).toBe(`52 deg 31' 12.00" N, 13 deg 24' 18.00" E`);
		expect(link.getAttribute("href")).toBe("https://www.google.com/maps/search/?api=1&query=52.52,13.405");
		expect(link.target).toBe("_blank");
		expect(link.rel).toBe("noopener noreferrer");
		expect(link.textContent).toBe("Open in Maps ↗");
	});

	it("renders no link when GPS is empty", () => {
		appendLocation(dd, "");
		expect(dd.querySelector("a")).toBeNull();
		expect(dd.textContent).toBe("—");
	});

	it("shows unparseable text as plain text without a link or markup", () => {
		appendLocation(dd, `1.0, 2.0"><script>`);
		expect(dd.querySelector("a")).toBeNull();
		expect(dd.querySelector("script")).toBeNull();
		expect(dd.textContent).toBe(`1.0, 2.0"><script>`);
	});

	it("replaces previous content when re-rendered for another item", () => {
		appendLocation(dd, "52.52, 13.405");
		appendLocation(dd, "");
		expect(dd.querySelector("a")).toBeNull();
		appendLocation(dd, "10, 20");
		expect(dd.querySelectorAll("a").length).toBe(1);
		expect(dd.querySelector("a")?.getAttribute("href")).toContain("query=10,20");
	});

	it("uses the desktop bridge and cancels navigation when available", () => {
		const open = vi.fn();
		window.pywebview = { api: { open_external_url: open } };
		appendLocation(dd, "52.52, 13.405");
		const click = new MouseEvent("click", { bubbles: true, cancelable: true });
		(dd.querySelector("a") as HTMLAnchorElement).dispatchEvent(click);
		expect(open).toHaveBeenCalledWith("https://www.google.com/maps/search/?api=1&query=52.52,13.405");
		expect(click.defaultPrevented).toBe(true);
	});

	it("lets the browser follow the link when there is no desktop bridge", () => {
		appendLocation(dd, "52.52, 13.405");
		const click = new MouseEvent("click", { bubbles: true, cancelable: true });
		(dd.querySelector("a") as HTMLAnchorElement).dispatchEvent(click);
		expect(click.defaultPrevented).toBe(false);
	});
});
