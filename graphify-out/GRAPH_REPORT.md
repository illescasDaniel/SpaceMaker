# Graph Report - SpaceMaker  (2026-09-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1390 nodes · 3565 edges · 71 communities (57 shown, 14 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 456 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8f30d91d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70

## God Nodes (most connected - your core abstractions)
1. `AppServices` - 107 edges
2. `create_fastapi_app()` - 92 edges
3. `LibraryFolder` - 75 edges
4. `BundledTool` - 52 edges
5. `FakeFileSystem` - 47 edges
6. `FileSystemPort` - 43 edges
7. `ConvertMedia` - 39 edges
8. `ToolRunner` - 33 edges
9. `bootstrapDesktopShell()` - 33 edges
10. `require_loopback()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `test_given_file_and_folder_when_build_share_manifest_then_one_row_each()` --calls--> `build_share_manifest()`  [INFERRED]
  tests/unit/test_file_share_manifest.py → src/spacemaker/application/file_share_manifest.py
- `test_given_payload_when_encode_qr_svg_then_white_background()` --calls--> `encode_qr_svg()`  [INFERRED]
  tests/unit/test_qr_svg.py → src/spacemaker/adapters/inbound/web/qr_svg.py
- `FakeInstaller` --uses--> `ToolInstallResult`  [INFERRED]
  tests/unit/test_managed_tools.py → src/spacemaker/ports/outbound/tool_installer.py
- `test_given_missing_file_when_delete_then_false()` --uses--> `DeleteGalleryItem`  [INFERRED]
  tests/unit/test_delete_gallery_item.py → src/spacemaker/application/delete_gallery_item.py
- `FakeFileSystem` --uses--> `LibraryFolder`  [INFERRED]
  tests/unit/fakes.py → src/spacemaker/domain/library.py

## Import Cycles
- None detected.

## Communities (71 total, 14 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (101): api(), appendThumbCell(), applyConnectionPanels(), applyGalleryExport(), applyGalleryFirewallHints(), applyState(), bindGalleryUi(), bindInfoPanelToggle() (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (46): spacemaker_application_managed_tools, spacemaker_domain_managed_tool, spacemaker_ports_outbound_tool_installer, ManagedToolsService, Path, True when a catalog tool is not yet present in the managed folder (PATH…, is_dev_mode(), app_icon_path() (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (27): AdbDevice, spacemaker_adapters_outbound_device_adb_repository, spacemaker_adapters_outbound_device_afc_repository, spacemaker_adapters_outbound_device_factory, spacemaker_adapters_outbound_device_mtp_repository, AdbDeviceRepository, Path, AfcDeviceRepository (+19 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (48): spacemaker_application_easy_session, spacemaker_application_wizard_state, spacemaker_domain_app_module, spacemaker_domain_connection, spacemaker_domain_convert_policy, spacemaker_domain_jobs, spacemaker_domain_ui_mode, spacemaker_domain_wizard (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (48): fastapi_testclient, fixture, log(), run_step(), checks.sh script, lib_find_repo_root(), lib_require_venv(), lib_uv_run() (+40 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (28): json, spacemaker_adapters_outbound_tools_catalog_installer, spacemaker_application_file_share_manifest, catalog_path(), CatalogToolInstaller, Any, Path, load_platform_catalog() (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (31): create_fastapi_app(), convert_stop(), easy_bootstrap(), extract_pause(), extract_resume(), extract_start(), extract_stop(), extract_upload_qr() (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (24): spacemaker_domain_conversion, count_image_files_in_library_folder(), ConversionRoute, image_avif_relative_path(), output_exceeds_rollback_threshold(), PlannedOutput, StrEnum, relative_parent_stem() (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (26): concurrent_futures, dataclasses, enum, secrets, spacemaker_domain_source_folders, AppSession, ExtractMedia, build_share_manifest() (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (17): adbutils, os, main(), Offscreen Qt WebEngine smoke test (post-prune AppDir venv)., pathlib, Dispatch quality gate to checks.sh (via bash on Windows)., shutil, spacemaker_domain_library_paths (+9 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (8): DeleteGalleryItem, ErrorRecovery, ReceiveUploadedMedia, UploadOutcome, LibraryFolder, FileSystemPort, Protocol, test_given_converted_file_when_delete_then_removed_and_thumb_cleared()

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (27): useAriaPropsSupportedByRole, useSemanticElements, useArrowFunction, files, includes, formatter, enabled, indentStyle (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (15): collections_abc, hashlib, ExportFriendlyMedia, ExportResult, export_cache_filename(), ExportFormat, ExportJobPhase, is_friendly_h264_aac_mp4() (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (24): bundle_root(), bundled_tool_path(), BundledTool, _executable_file(), managed_tool_present(), missing_bundled_tools(), Path, StrEnum (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.21
Nodes (15): ConvertMedia, FakeMediaConverter, FakeMediaProbe, test_given_stop_after_first_file_when_convert_then_stops_early(), _paths(), test_given_avif_in_originals_when_convert_then_moves_to_converted(), test_given_encode_fails_twice_when_convert_then_moves_to_error(), test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs() (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (9): spacemaker_application_error_recovery, spacemaker_application_receive_uploaded_media, StrEnum, UploadDisposition, FakeFileSystem, test_given_error_files_when_move_all_to_converted_then_empties_error(), Path, test_given_existing_same_size_when_wifi_upload_then_skipped() (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (10): spacemaker_adapters_outbound_filesystem_local, spacemaker_application_delete_gallery_item, spacemaker_application_get_gallery_item, LocalFileSystem, test_given_missing_file_when_delete_then_false(), test_given_converted_file_when_get_item_then_returns_detail(), test_given_missing_file_when_get_item_then_none(), Path (+2 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (19): FastAPI, ipaddress, spacemaker_adapters_inbound_web_client_access, no_cache_shell_assets(), websocket_endpoint(), is_loopback_client_host(), require_loopback_websocket(), starlette_requests (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.21
Nodes (16): GenerateGallery, datetime, days_in_month(), days_with_media(), gallery_item(), GalleryItem, group_timeline(), items_for_day() (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (10): GalleryItemDetail, GetGalleryItem, datetime, GalleryDisplayMetadata, is_inline_preview_video(), MediaProbePort, datetime, Protocol (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (20): asyncio, BaseModel, fastapi_responses, fastapi_staticfiles, io, pydantic, segno, _attachment_named() (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (17): _apply_native_style(), install_qt_native_style(), setup_app(), Apply a platform-appropriate QStyle so pywebview's own QtWidgets dialogs (close…, install_qt_webengine_gpu_flags(), Windows: work around a black/frozen WebEngine surface that only repaints when…, Windows: point uvicorn's `loop=` at asyncio.SelectorEventLoop instead of its…, uvicorn_loop_for_platform() (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.20
Nodes (18): contextlib, logging, _delete_top_level_widgets(), _disconnect_signal(), _disconnect_webengine_bindings(), _drain_qt_events(), finalize_qt_after_webview(), install_qt_webengine_shutdown_fix() (+10 more)

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (15): socket, server_info(), _firewalld_port_open(), FirewallStatus, _lan_connect_probe(), probe_gallery_port(), _try_tcp_connect(), _ufw_config_enabled() (+7 more)

### Community 25 - "Community 25"
Cohesion: 0.21
Nodes (16): spacemaker_adapters_inbound_web_spa_entry, gallery_page(), root_page(), _spa_file(), is_loopback_host(), is_private_lan_host(), normalize_host(), StrEnum (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (9): spacemaker_application_extract_media, spacemaker_domain_gallery_metadata, spacemaker_domain_video_encode, spacemaker_ports_outbound_device_repository, FakeDeviceRepository, datetime, test_given_copy_mode_when_extract_then_file_stays_on_device(), test_given_existing_original_with_same_size_when_extract_then_skips_pull() (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (5): qtpy, spacemaker_adapters_inbound, test_given_filter_installed_when_messages_logged_then_benign_swallowed_and_others_forwarded(), fake_previous_handler(), fake_qinstall()

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (13): re, spacemaker_adapters_outbound_media_raw_preview, extract_raw_embedded_jpeg(), Path, raw_embedded_preview_available(), is_raw_extension(), Path, _skip_on_windows (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (14): argparse, Popen, _bypass_components_setup(), _ephemeral_port(), main(), _prepare_smoke_home(), Path, Capture the SpaceMaker Home hub for README (offscreen Qt WebEngine). (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.24
Nodes (11): spacemaker_adapters_outbound_media_ffmpeg_encoders, av1_encoder_ffmpeg_args(), h264_hw_encoder_ffmpeg_args(), hardware_video_encoder_from_ffmpeg_encoders(), HardwareVideoEncoder, StrEnum, subprocess, tempfile (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (4): RuntimeError, Path, SubprocessMediaConverter, ToolExecutionError

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (4): spacemaker_domain_extract_control, ExtractJobControl, test_given_pause_requested_when_after_file_then_marked_paused(), test_given_stop_requested_when_before_next_file_then_aborts_queue()

### Community 33 - "Community 33"
Cohesion: 0.20
Nodes (9): spacemaker_domain_upload_paths, DocumentUploadDisposition, DocumentUploadOutcome, StrEnum, ReceiveUploadedDocuments, is_safe_upload_relative_path(), normalize_upload_relative_path(), test_given_dotdot_when_normalize_then_none() (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (10): DesktopApi, convert_start(), defaults(), default_library_root(), normalize_library_root(), pictures_directory(), If the user picked a bucket folder (e.g. …/originals), use the library root…, Path (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (10): Path, Guards against Cursor/Claude Code agent-context drift and re-bloat. AGENTS.md…, Split a `---`-delimited YAML frontmatter block from the body below it., _rule_pairs(), _split_frontmatter(), test_given_a_rule_pair_when_comparing_bodies_then_they_are_byte_identical(), test_given_a_rule_pair_when_comparing_scoping_then_always_apply_and_globs_are_equivalent(), test_given_cursor_rules_dir_when_listing_pairs_then_every_cursor_rule_has_a_claude_counterpart() (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (6): dedupe_share_selection_paths(), EmptyShareSelectionError, User selection resolves to zero shareable files., Keep first occurrence of each top-level path (compared by resolved absolute…, test_given_duplicate_paths_when_dedupe_share_selection_then_keeps_first(), ValueError

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (4): on_progress(), Protocol, WebSocketLike, GalleryExportJob

### Community 40 - "Community 40"
Cohesion: 0.36
Nodes (4): CompletedProcess, Path, ToolRunner, is_frozen()

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (11): gallery_calendar(), gallery_day(), gallery_item_delete(), gallery_item_detail(), gallery_timeline(), library_counts(), _gallery_item_dict(), _metadata_dict() (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (10): devDependencies, @biomejs/biome, @fortawesome/fontawesome-free, name, private, scripts, check, fix (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (4): spacemaker_application_receive_uploaded_documents, FakeFs, Path, test_given_valid_relative_path_when_ingest_then_saved_under_dest_root()

### Community 44 - "Community 44"
Cohesion: 0.24
Nodes (10): FileResponse, _attachment_filename(), gallery_export_file(), gallery_export_start(), media_file(), thumb_file(), _no_cache_file(), _path_is_under_base() (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (6): Image, pil, main(), Path, Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-…, _save_resize()

### Community 46 - "Community 46"
Cohesion: 0.24
Nodes (8): spacemaker_adapters_outbound_media_subprocess_converter, spacemaker_adapters_outbound_media_subprocess_probe, spacemaker_adapters_outbound_media_tool_runner, spacemaker_application_convert_media, _install_tool_scripts(), Path, _skip_on_windows, test_given_dng_when_magick_cannot_read_then_converts_embedded_preview()

### Community 47 - "Community 47"
Cohesion: 0.31
Nodes (6): datetime, spacemaker_application_generate_gallery, spacemaker_domain_gallery, spacemaker_domain_library, spacemaker_domain_media, test_given_error_files_when_count_then_warning_visible()

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): importlib_metadata, app_release_info(), app_version(), Release identity (mirrors [project] in pyproject.toml)., SpaceMaker — local media backup, convert, and gallery., test_given_installed_package_when_reading_release_info_then_matches_1_0()

### Community 49 - "Community 49"
Cohesion: 0.46
Nodes (7): convert_to_av1(), convert_to_avif(), detect_encoder(), get_bitrate_bps(), is_browser_compatible(), process_file(), convert_all_1_1.sh script

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (3): Path, RecordingConverter, test_given_nested_original_when_convert_then_creates_converted_parent()

### Community 52 - "Community 52"
Cohesion: 0.38
Nodes (6): httpx, _free_port(), Launches the real `spacemaker` process (not TestClient) to catch startup bugs…, _read_output_into(), test_given_real_process_when_server_only_starts_then_boots_and_serves(), time

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (6): APPDIR, QT_QPA_PLATFORM, build-appdir.sh script, SPACEMAKER_BUNDLE_ROOT, UV_LINK_MODE, UV_PYTHON_PREFERENCE

### Community 54 - "Community 54"
Cohesion: 0.29
Nodes (5): APPIMAGE_EXTRACT_AND_RUN, HOME, PATH, QT_QPA_PLATFORM, smoke-appimage.sh script

### Community 55 - "Community 55"
Cohesion: 0.43
Nodes (3): on_progress(), ConnectionMethod, StrEnum

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (6): _capture_with_webengine(), fail(), on_load_ok(), poll_home(), on_result(), save_png()

### Community 57 - "Community 57"
Cohesion: 0.33
Nodes (5): spacemaker_application_export_friendly_media, spacemaker_domain_gallery_export, spacemaker_domain_web_compat, test_given_avif_in_converted_when_export_jpeg_then_writes_cache(), test_given_jpeg_in_converted_when_export_jpeg_then_skips_encode()

### Community 60 - "Community 60"
Cohesion: 0.53
Nodes (5): MonkeyPatch, Path, _skip_on_windows, test_given_managed_ffmpeg_without_hw_when_path_allowed_then_prefers_system_ffmpeg(), test_given_nonzero_exit_when_run_then_raises_with_stderr()

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (5): install_benign_shutdown_warning_filter(), handler(), _is_benign_shutdown_warning(), Match known-benign async WebEngine/Qt teardown log noise (see…, Silence known-benign async WebEngine/Qt shutdown log noise without touching…

### Community 62 - "Community 62"
Cohesion: 0.83
Nodes (3): keep_binding(), rm_rf(), prune_pyqt6.sh script

## Knowledge Gaps
- **41 isolated node(s):** `PlannedOutput`, `useAriaPropsSupportedByRole`, `useSemanticElements`, `useArrowFunction`, `includes` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 306 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppServices` connect `Community 14` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 12`, `Community 13`, `Community 15`, `Community 17`, `Community 19`, `Community 20`, `Community 21`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 35`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 44`, `Community 50`, `Community 55`, `Community 58`, `Community 69`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `LibraryFolder` connect `Community 10` to `Community 2`, `Community 3`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 19`, `Community 20`, `Community 21`, `Community 26`, `Community 44`, `Community 46`, `Community 47`, `Community 50`, `Community 51`, `Community 57`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `create_fastapi_app()` connect `Community 6` to `Community 34`, `Community 3`, `Community 4`, `Community 38`, `Community 8`, `Community 41`, `Community 10`, `Community 44`, `Community 12`, `Community 14`, `Community 48`, `Community 18`, `Community 21`, `Community 55`, `Community 24`, `Community 25`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `AppServices` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`AppServices` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `create_fastapi_app()` (e.g. with `lifespan()` and `SpaEntry`) actually correct?**
  _`create_fastapi_app()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `LibraryFolder` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`LibraryFolder` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `BundledTool` (e.g. with `AfcDeviceRepository` and `device_repository_for()`) actually correct?**
  _`BundledTool` has 25 INFERRED edges - model-reasoned connections that need verification._