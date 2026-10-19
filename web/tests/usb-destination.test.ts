import { describe, expect, it } from "vitest";
import { isAbsoluteDestination } from "../src/usb.ts";

describe("isAbsoluteDestination", () => {
	it("given posix, drive-letter and UNC paths then they are absolute", () => {
		expect(isAbsoluteDestination("/home/u/Backups")).toBe(true);
		expect(isAbsoluteDestination("C:\\Users\\u")).toBe(true);
		expect(isAbsoluteDestination("\\\\server\\share")).toBe(true);
	});

	it("given relative or empty text then it is not absolute", () => {
		expect(isAbsoluteDestination("Backups/phone")).toBe(false);
		expect(isAbsoluteDestination("  ")).toBe(false);
	});
});
