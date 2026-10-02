/** GPS display text (ExifTool) → validated point → Google Maps link. See specs/gallery-open-in-maps/SPEC.md. */

export interface GpsPoint {
	lat: number;
	lon: number;
}

const NUM = "(\\d{1,3}(?:\\.\\d+)?)";
const DMS = new RegExp(
	`^${NUM}\\s*(?:deg|°)\\s*${NUM}\\s*'\\s*${NUM}\\s*"\\s*([NS])\\s*,\\s*${NUM}\\s*(?:deg|°)\\s*${NUM}\\s*'\\s*${NUM}\\s*"\\s*([EW])$`,
);
const DECIMAL_HEMI = new RegExp(`^${NUM}\\s*°?\\s*([NS])\\s*,\\s*${NUM}\\s*°?\\s*([EW])$`);
const SIGNED_PAIR = /^(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)$/;

function round6(value: number): number {
	return Math.round(value * 1e6) / 1e6;
}

function validPoint(lat: number, lon: number): GpsPoint | null {
	if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
		return null;
	}
	return { lat: round6(lat), lon: round6(lon) };
}

export function parseGps(text: string): GpsPoint | null {
	const value = (text || "").trim();
	const dms = DMS.exec(value);
	if (dms) {
		const [, d1, m1, s1, ns, d2, m2, s2, ew] = dms;
		if (Number(m1) >= 60 || Number(s1) >= 60 || Number(m2) >= 60 || Number(s2) >= 60) {
			return null;
		}
		const lat = Number(d1) + Number(m1) / 60 + Number(s1) / 3600;
		const lon = Number(d2) + Number(m2) / 60 + Number(s2) / 3600;
		return validPoint(ns === "S" ? -lat : lat, ew === "W" ? -lon : lon);
	}
	const hemi = DECIMAL_HEMI.exec(value);
	if (hemi) {
		const lat = Number(hemi[1]);
		const lon = Number(hemi[3]);
		return validPoint(hemi[2] === "S" ? -lat : lat, hemi[4] === "W" ? -lon : lon);
	}
	const pair = SIGNED_PAIR.exec(value);
	if (pair) {
		return validPoint(Number(pair[1]), Number(pair[2]));
	}
	return null;
}

function fmt(value: number): string {
	const text = value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
	return text === "-0" ? "0" : text;
}

export function mapsUrl(point: GpsPoint): string {
	return `https://www.google.com/maps/search/?api=1&query=${fmt(point.lat)},${fmt(point.lon)}`;
}

/** Fill a Location `<dd>`: raw text, plus an "Open in Maps" link only when the text parses. */
export function appendLocation(dd: HTMLElement, gps: string): void {
	dd.className = "gallery-meta-location";
	const point = parseGps(gps);
	if (!gps) {
		dd.textContent = "—";
		return;
	}
	const text = document.createElement("span");
	text.textContent = gps;
	dd.replaceChildren(text);
	if (!point) {
		return;
	}
	const url = mapsUrl(point);
	const link = document.createElement("a");
	link.className = "gallery-open-maps";
	link.href = url;
	link.target = "_blank";
	link.rel = "noopener noreferrer";
	link.textContent = "Open in Maps ↗";
	link.addEventListener("click", (event) => {
		const open = window.pywebview?.api?.open_external_url;
		if (open) {
			// The embedded webview may ignore target=_blank; the desktop bridge opens the system browser.
			event.preventDefault();
			void Promise.resolve(open(url)).catch(() => undefined);
		}
	});
	dd.appendChild(link);
}
