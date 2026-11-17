# Desktop shell
Updated: 2026-11-17. The desktop window: pywebview backends, Qt WebEngine quirks, shell versioning and shared UI components.

## Now
Windows and macOS use native pywebview backends, Linux Qt WebEngine ([native-pywebview-win-mac](../notes/native-pywebview-win-mac.md)); the shell version is an automatic fingerprint ([ui-shell-fingerprint-import-map](../notes/ui-shell-fingerprint-import-map.md)); web code is fully typed TS ([web-ts-typing-pass-drop-r-registry](../notes/web-ts-typing-pass-drop-r-registry.md)); copying text must avoid the clipboard API in Qt ([pywebview-qt-clipboard-permission](../notes/pywebview-qt-clipboard-permission.md)).

## How it got here
- 2026-09-23 versioned profile dir, then a single shell-version constant (2026-09-27), then an automatic fingerprint (2026-09-29) ([note](../notes/ui-shell-fingerprint-import-map.md)).
- 2026-09-24 Qt shutdown warnings: not pursued, then narrowed to a log filter ([note](../notes/qt-shutdown-warnings-log-filter.md)).
- 2026-09-24 SelectorEventLoop via a factory, fixed the same day to name the loop class ([note](../notes/uvicorn-selector-loop-class.md)).

## Notes
- [One ⓘ helper and one URL field component for the desktop UI](../notes/info-panels-and-url-field-components.md) 2026-10-18: one info-panel binding and one copyable URL field; execCommand fallback because LAN pages are plain http
- [Clipboard API fails in the pywebview Qt shell](../notes/pywebview-qt-clipboard-permission.md) 2026-10-18: navigator.clipboard fails in the pywebview Qt shell (feature-permission TypeError); use execCommand first
- [Full `web/src/*.ts` typing pass: drop `R` registry, drop `@ts-nocheck`, scope Biome's new strict rules via `overrides`](../notes/web-ts-typing-pass-drop-r-registry.md) 2026-09-29: all web/src/*.ts fully typed, @ts-nocheck and the R registry removed; guarded by a test
- [Enable Chromium smooth wheel scrolling in the Qt WebEngine desktop shell](../notes/qt-smooth-wheel-scrolling.md) 2026-09-29: Chromium smooth scrolling enabled in Qt WebEngine; user-set flags kept
- [Drop manual shell-version bumps; fingerprint + import map + clear HTTP cache on launch](../notes/ui-shell-fingerprint-import-map.md) 2026-09-29: shell version is an automatic hash of static/js; import map + clear HTTP cache on launch; no manual bumps
- [Home hub: 3-column 4:3 tiles + floating footer (UI-only)](../notes/home-hub-3-column-tiles.md) 2026-09-27: Home hub is a 3-column grid of 4:3 tiles with a floating footer
- [Native pywebview backend on Windows/macOS; Qt WebEngine kept Linux-only](../notes/native-pywebview-win-mac.md) 2026-09-24: edgechromium on Windows, cocoa on macOS; Qt WebEngine only on Linux
- [`QDxgiVSyncService`/`QThreadStorage` shutdown warnings: narrowed the earlier "not pursuing further" decision to a log filter, since the actual ask was noise, not the race](../notes/qt-shutdown-warnings-log-filter.md) 2026-09-24: benign Qt shutdown warnings filtered from logs; teardown timing left alone
- [Fixed the SelectorEventLoop fix itself: uvicorn's custom `loop=` string must resolve to the loop class directly, not a factory function; added a real-process smoke test](../notes/uvicorn-selector-loop-class.md) 2026-09-24: uvicorn loop= must name the loop class (asyncio:SelectorEventLoop), not a factory
- [Windows WebEngine freeze/black-surface fix attempts; QtWidgets native style (windows11/Fusion)](../notes/windows-webengine-freeze-native-style.md) 2026-09-24: Windows WebEngine freeze/black-surface workarounds; native QtWidgets style
- [Qt WebEngine shutdown teardown hardened further for Windows](../notes/qt-webengine-shutdown-teardown.md) 2026-09-24: idempotent WebEngine teardown and a finalize pass after pywebview's loop exits
- [System theme and self-hosted Font Awesome for gallery nav](../notes/system-theme-self-hosted-fa.md) 2026-09-23: one theme.css with prefers-color-scheme; vendored Font Awesome (CSP font-src self)
- [Desktop window 4:3 geometry in one module](../notes/desktop-window-4-3-geometry.md) 2026-09-23: window geometry in one module, 4:3 default and 800x600 minimum
- [Home hub modules and Qt WebEngine shell cache](../notes/home-hub-modules-shell-cache.md) 2026-09-23: Home hub modules, one LAN session at a time; versioned WebEngine profile dir

## History (superseded)
- [Qualify bare cross-module shell helpers as `R.*` after the TS split](../notes/shell-helpers-qualified-r.md) 2026-09-29 → superseded by web-ts-typing-pass-drop-r-registry
- [Keep pre-rename `R.*` aliases on the shell runtime registry](../notes/shell-r-aliases-kept.md) 2026-09-29 → superseded by web-ts-typing-pass-drop-r-registry
- [UI shell version: single source of truth + silent auto-reload (no mismatch banner)](../notes/ui-shell-version-single-source.md) 2026-09-27 → superseded by ui-shell-fingerprint-import-map
- [`QDxgiVSyncService`/`QThreadStorage` shutdown warnings: confirmed benign, confirmed unrelated to the WebEngine freeze fix, not pursuing further](../notes/qt-shutdown-warnings-not-pursued.md) 2026-09-24 → superseded by qt-shutdown-warnings-log-filter
- [Windows ProactorEventLoop ConnectionResetError noise: switched uvicorn to SelectorEventLoop via `loop=` factory, not the deprecated asyncio policy API](../notes/uvicorn-selector-loop-factory.md) 2026-09-24 → superseded by uvicorn-selector-loop-class
