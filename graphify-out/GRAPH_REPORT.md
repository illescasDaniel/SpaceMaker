# Graph Report - SpaceMaker  (2026-09-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1398 nodes · 3571 edges · 82 communities (64 shown, 18 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 456 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eee4569f`
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
- Community 68
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81

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
- `test_given_avif_in_converted_when_export_jpeg_then_writes_cache()` --uses--> `ExportFriendlyMedia`  [INFERRED]
  tests/unit/test_gallery_export.py → src/spacemaker/application/export_friendly_media.py
- `test_given_jpeg_in_converted_when_export_jpeg_then_skips_encode()` --uses--> `ExportFriendlyMedia`  [INFERRED]
  tests/unit/test_gallery_export.py → src/spacemaker/application/export_friendly_media.py
- `test_given_avif_in_converted_when_export_jpeg_then_writes_cache()` --uses--> `ExportFormat`  [INFERRED]
  tests/unit/test_gallery_export.py → src/spacemaker/domain/gallery_export.py
- `test_given_jpeg_in_converted_when_export_jpeg_then_skips_encode()` --uses--> `ExportFormat`  [INFERRED]
  tests/unit/test_gallery_export.py → src/spacemaker/domain/gallery_export.py
- `test_given_stop_after_first_file_when_convert_then_stops_early()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media_control.py → src/spacemaker/application/convert_media.py

## Import Cycles
- None detected.

## Communities (82 total, 18 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (101): api(), appendThumbCell(), applyConnectionPanels(), applyGalleryExport(), applyGalleryFirewallHints(), applyState(), bindGalleryUi(), bindInfoPanelToggle() (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (50): spacemaker_domain_conversion, Path, SubprocessThumbnailGenerator, ConvertMedia, ExportFriendlyMedia, ExportResult, GalleryItemDetail, GetGalleryItem (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (48): fastapi_testclient, fixture, log(), run_step(), checks.sh script, lib_find_repo_root(), lib_require_venv(), lib_uv_run() (+40 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (16): spacemaker_application_receive_uploaded_documents, spacemaker_domain_upload_paths, ErrorRecovery, DocumentUploadOutcome, ReceiveUploadedDocuments, ReceiveUploadedMedia, UploadOutcome, is_safe_upload_relative_path() (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (29): _attachment_named(), create_fastapi_app(), convert_start(), convert_stop(), easy_bootstrap(), extract_pause(), extract_resume(), extract_start() (+21 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (33): DesktopApi, defaults(), Path, app_icon_path(), bundle_resource_root(), clear_components_setup_complete(), components_setup_complete_marker(), default_documents_receive_root() (+25 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (25): spacemaker_application_wizard_state, spacemaker_domain_jobs, originals_count_for(), wizard_actions(), can_start_convert(), convert_control_flags(), extract_control_flags(), JobPhase (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (13): spacemaker_application_delete_gallery_item, spacemaker_application_get_gallery_item, LocalFileSystem, DeleteGalleryItem, LibraryFolder, StrEnum, test_given_converted_file_when_delete_then_removed_and_thumb_cleared(), test_given_missing_file_when_delete_then_false() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (27): useAriaPropsSupportedByRole, useSemanticElements, useArrowFunction, files, includes, formatter, enabled, indentStyle (+19 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (4): AbstractEventLoop, AppServices, datetime, Path

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (12): shutil, ManagedToolsService, True when a catalog tool is not yet present in the managed folder (PATH…, is_dev_mode(), components_setup_hint(), Any, Optional copy + install command for the Components setup screen., _windows_winget_ids() (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (22): spacemaker_application_file_share_manifest, build_share_manifest(), count_shareable_files_in_root(), dedupe_share_selection_paths(), is_path_under_roots(), prune_share_selection_paths(), Path, Write folder contents to dest, preserving relative paths inside the archive. (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.20
Nodes (14): FakeMediaConverter, FakeMediaProbe, test_given_stop_after_first_file_when_convert_then_stops_early(), _paths(), test_given_avif_in_originals_when_convert_then_moves_to_converted(), test_given_encode_fails_twice_when_convert_then_moves_to_error(), test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs(), test_given_low_bitrate_mp4_when_convert_then_move_as_is() (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (19): FastAPI, ipaddress, spacemaker_adapters_inbound_web_client_access, no_cache_shell_assets(), websocket_endpoint(), is_loopback_client_host(), require_loopback_websocket(), starlette_requests (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (22): logging, _delete_top_level_widgets(), _disconnect_signal(), _disconnect_webengine_bindings(), _drain_qt_events(), finalize_qt_after_webview(), install_benign_shutdown_warning_filter(), handler() (+14 more)

### Community 15 - "Community 15"
Cohesion: 0.19
Nodes (12): collections_abc, spacemaker_adapters_outbound_media_ffmpeg_encoders, av1_encoder_ffmpeg_args(), h264_hw_encoder_ffmpeg_args(), hardware_video_encoder_from_ffmpeg_encoders(), HardwareVideoEncoder, StrEnum, subprocess (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (17): install_qt_webengine_gpu_flags(), Windows: work around a black/frozen WebEngine surface that only repaints when…, Windows: point uvicorn's `loop=` at asyncio.SelectorEventLoop instead of its…, uvicorn_loop_for_platform(), _apply_qt_window_icon(), _default_gui_backend(), main(), on_closing() (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (14): GenerateGallery, datetime, days_in_month(), days_with_media(), gallery_item(), GalleryItem, group_timeline(), items_for_day() (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (9): adbutils, os, pathlib, spacemaker_domain_library_paths, True for device or library paths under skipped folders (e.g. .thumbnails)., skip_library_relative_path(), skip_media_path(), test_given_normal_path_when_skip_media_path_then_false() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (15): socket, server_info(), _firewalld_port_open(), FirewallStatus, _lan_connect_probe(), probe_gallery_port(), _try_tcp_connect(), _ufw_config_enabled() (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (13): spacemaker_application_easy_session, spacemaker_domain_app_module, spacemaker_domain_ui_mode, AppSession, should_auto_start_wifi_extract(), AppModule, LanSessionKind, StrEnum (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (14): spacemaker_application_error_recovery, spacemaker_application_export_friendly_media, spacemaker_domain_gallery_export, spacemaker_domain_gallery_metadata, spacemaker_domain_library, spacemaker_domain_video_encode, spacemaker_domain_web_compat, spacemaker_domain_wizard (+6 more)

### Community 22 - "Community 22"
Cohesion: 0.22
Nodes (4): AfcDeviceRepository, apple_usb_plugged(), Path, usbmuxd_running()

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (4): CatalogToolInstaller, Any, Path, ToolInstallResult

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (16): BaseModel, fastapi_responses, fastapi_staticfiles, pydantic, GalleryExportBody, GalleryOpenBody, LibraryOpenFolderBody, ModuleEnterBody (+8 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (14): CompletedProcess, BundledTool, StrEnum, resolve_tool_path(), Composition root and runtime paths., MonkeyPatch, Path, test_given_managed_file_exists_when_resolve_then_uses_managed() (+6 more)

### Community 26 - "Community 26"
Cohesion: 0.21
Nodes (16): spacemaker_adapters_inbound_web_spa_entry, gallery_page(), root_page(), _spa_file(), is_loopback_host(), is_private_lan_host(), normalize_host(), StrEnum (+8 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (7): spacemaker_application_receive_uploaded_media, StrEnum, UploadDisposition, FakeFileSystem, Path, test_given_existing_same_size_when_wifi_upload_then_skipped(), test_given_new_file_when_wifi_upload_then_saved()

### Community 28 - "Community 28"
Cohesion: 0.21
Nodes (12): asyncio, concurrent_futures, contextlib, secrets, parse_source_folders(), path_matches_source_folders(), StrEnum, SourceFolder (+4 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (5): qtpy, spacemaker_adapters_inbound, test_given_filter_installed_when_messages_logged_then_benign_swallowed_and_others_forwarded(), fake_previous_handler(), fake_qinstall()

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (11): spacemaker_adapters_outbound_filesystem_local, spacemaker_adapters_outbound_media_subprocess_converter, spacemaker_adapters_outbound_media_subprocess_probe, spacemaker_application_convert_media, _install_tool_scripts(), Path, _skip_on_windows, test_given_dng_when_magick_cannot_read_then_converts_embedded_preview() (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (7): spacemaker_application_extract_media, spacemaker_ports_outbound_device_repository, DeviceInfo, FakeDeviceRepository, test_given_copy_mode_when_extract_then_file_stays_on_device(), test_given_existing_original_with_same_size_when_extract_then_skips_pull(), test_given_thumbnails_path_when_extract_then_skips_pull()

### Community 32 - "Community 32"
Cohesion: 0.20
Nodes (11): spacemaker_application_managed_tools, spacemaker_domain_managed_tool, spacemaker_ports_outbound_tool_installer, FakeInstaller, Path, test_given_catalog_installs_when_ensure_then_places_file(), fake_install(), test_given_continue_marker_on_disk_when_new_service_then_setup_not_pending() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.22
Nodes (13): Popen, _bypass_components_setup(), _ephemeral_port(), main(), _prepare_smoke_home(), Path, Capture the SpaceMaker Home hub for README (offscreen Qt WebEngine)., _server_env() (+5 more)

### Community 34 - "Community 34"
Cohesion: 0.22
Nodes (4): re, datetime, SubprocessMediaProbe, is_raw_extension()

### Community 35 - "Community 35"
Cohesion: 0.25
Nodes (4): RuntimeError, Path, SubprocessMediaConverter, ToolExecutionError

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (4): spacemaker_domain_extract_control, ExtractJobControl, test_given_pause_requested_when_after_file_then_marked_paused(), test_given_stop_requested_when_before_next_file_then_aborts_queue()

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (9): argparse, main(), Offscreen Qt WebEngine smoke test (post-prune AppDir venv)., Dispatch quality gate to checks.sh (via bash on Windows)., _apply_native_style(), install_qt_native_style(), setup_app(), Apply a platform-appropriate QStyle so pywebview's own QtWidgets dialogs (close… (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.22
Nodes (10): Path, Guards against Cursor/Claude Code agent-context drift and re-bloat. AGENTS.md…, Split a `---`-delimited YAML frontmatter block from the body below it., _rule_pairs(), _split_frontmatter(), test_given_a_rule_pair_when_comparing_bodies_then_they_are_byte_identical(), test_given_a_rule_pair_when_comparing_scoping_then_always_apply_and_globs_are_equivalent(), test_given_cursor_rules_dir_when_listing_pairs_then_every_cursor_rule_has_a_claude_counterpart() (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.24
Nodes (11): spacemaker_domain_convert_policy, convert_start_policy(), ConvertStartPolicy, StrEnum, should_auto_drain_after_upload(), should_requeue_convert_drain(), test_given_advanced_mode_when_convert_start_policy_then_stop_extract(), test_given_concurrent_and_remaining_when_should_requeue_then_true() (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (11): bundle_root(), bundled_tool_path(), _executable_file(), managed_tool_present(), missing_bundled_tools(), Path, Return (path, source) where source is 'managed' or 'path'., ImageMagick winget/installer often lands under Program Files without updating… (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (4): on_progress(), Protocol, WebSocketLike, GalleryExportJob

### Community 42 - "Community 42"
Cohesion: 0.29
Nodes (5): dataclasses, enum, DocumentUploadDisposition, StrEnum, typing

### Community 43 - "Community 43"
Cohesion: 0.17
Nodes (6): io, json, segno, spacemaker_adapters_outbound_tools_catalog_installer, Path, test_given_zip_flatten_when_install_then_places_exiftool_tree()

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (11): gallery_calendar(), gallery_day(), gallery_item_delete(), gallery_item_detail(), gallery_timeline(), library_counts(), _gallery_item_dict(), _metadata_dict() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (8): hashlib, catalog_path(), load_platform_catalog(), Any, Path, platform_catalog_key(), stat, tarfile

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (10): devDependencies, @biomejs/biome, @fortawesome/fontawesome-free, name, private, scripts, check, fix (+2 more)

### Community 48 - "Community 48"
Cohesion: 0.31
Nodes (9): spacemaker_adapters_outbound_media_raw_preview, extract_raw_embedded_jpeg(), Path, raw_embedded_preview_available(), Path, _skip_on_windows, test_given_exiftool_has_preview_when_available_then_true(), test_given_preview_bytes_when_extract_then_writes_jpeg() (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.24
Nodes (3): AdbDevice, AdbDeviceRepository, Path

### Community 51 - "Community 51"
Cohesion: 0.24
Nodes (10): FileResponse, _attachment_filename(), gallery_export_file(), gallery_export_start(), media_file(), thumb_file(), _no_cache_file(), _path_is_under_base() (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (6): Image, pil, main(), Path, Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-…, _save_resize()

### Community 53 - "Community 53"
Cohesion: 0.24
Nodes (9): spacemaker_adapters_outbound_device_adb_repository, spacemaker_adapters_outbound_device_afc_repository, spacemaker_adapters_outbound_device_factory, spacemaker_adapters_outbound_device_mtp_repository, spacemaker_domain_connection, device_repository_for(), test_given_adb_when_device_repository_for_then_adb_repo(), test_given_afc_when_device_repository_for_then_afc_repo() (+1 more)

### Community 54 - "Community 54"
Cohesion: 0.29
Nodes (7): spacemaker_adapters_outbound_media_tool_runner, ToolRunner, MonkeyPatch, Path, _skip_on_windows, test_given_managed_ffmpeg_without_hw_when_path_allowed_then_prefers_system_ffmpeg(), test_given_nonzero_exit_when_run_then_raises_with_stderr()

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): importlib_metadata, app_release_info(), app_version(), Release identity (mirrors [project] in pyproject.toml)., SpaceMaker — local media backup, convert, and gallery., test_given_installed_package_when_reading_release_info_then_matches_1_0()

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (8): spacemaker_adapters_inbound_web_qr_svg, extract_upload_qr(), gallery_qr(), receive_qr(), share_qr(), encode_qr_svg(), SVG QR with opaque white background (readable on dark UI themes)., test_given_payload_when_encode_qr_svg_then_white_background()

### Community 58 - "Community 58"
Cohesion: 0.36
Nodes (8): spacemaker_domain_source_folders, Path, test_given_100apple_at_mount_root_when_list_media_paths_then_prefixes_dcim(), test_given_afc_mount_when_extract_dcim_then_copies_to_originals(), test_given_dcim_heic_when_list_media_paths_then_lists_relative(), test_given_file_when_pull_and_size_then_match(), test_given_move_when_delete_device_file_then_removes_source(), test_given_photodata_when_list_media_paths_then_skips_non_camera_folders()

### Community 60 - "Community 60"
Cohesion: 0.32
Nodes (6): datetime, spacemaker_application_generate_gallery, spacemaker_domain_gallery, spacemaker_domain_media, test_given_converted_and_originals_when_calendar_days_then_converted_only(), test_given_converted_files_when_generate_then_lists_only_converted()

### Community 61 - "Community 61"
Cohesion: 0.46
Nodes (7): convert_to_av1(), convert_to_avif(), detect_encoder(), get_bitrate_bps(), is_browser_compatible(), process_file(), convert_all_1_1.sh script

### Community 63 - "Community 63"
Cohesion: 0.38
Nodes (6): httpx, _free_port(), Launches the real `spacemaker` process (not TestClient) to catch startup bugs…, _read_output_into(), test_given_real_process_when_server_only_starts_then_boots_and_serves(), time

### Community 64 - "Community 64"
Cohesion: 0.29
Nodes (6): APPDIR, QT_QPA_PLATFORM, build-appdir.sh script, SPACEMAKER_BUNDLE_ROOT, UV_LINK_MODE, UV_PYTHON_PREFERENCE

### Community 65 - "Community 65"
Cohesion: 0.29
Nodes (5): APPIMAGE_EXTRACT_AND_RUN, HOME, PATH, QT_QPA_PLATFORM, smoke-appimage.sh script

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (6): _capture_with_webengine(), fail(), on_load_ok(), poll_home(), on_result(), save_png()

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (3): Protocol, Download and place one tool into the managed tools directory., ToolInstallerPort

### Community 74 - "Community 74"
Cohesion: 0.83
Nodes (3): keep_binding(), rm_rf(), prune_pyqt6.sh script

## Knowledge Gaps
- **41 isolated node(s):** `PlannedOutput`, `web.sh script`, `@biomejs/biome`, `@fortawesome/fontawesome-free`, `name` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 312 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppServices` connect `Community 9` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 11`, `Community 15`, `Community 17`, `Community 20`, `Community 23`, `Community 24`, `Community 25`, `Community 28`, `Community 34`, `Community 35`, `Community 36`, `Community 39`, `Community 41`, `Community 44`, `Community 49`, `Community 51`, `Community 54`, `Community 55`, `Community 59`, `Community 67`, `Community 69`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `create_fastapi_app()` connect `Community 4` to `Community 1`, `Community 2`, `Community 56`, `Community 5`, `Community 6`, `Community 39`, `Community 7`, `Community 9`, `Community 44`, `Community 13`, `Community 51`, `Community 19`, `Community 20`, `Community 24`, `Community 57`, `Community 26`, `Community 28`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `LibraryFolder` connect `Community 7` to `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 9`, `Community 12`, `Community 17`, `Community 18`, `Community 21`, `Community 24`, `Community 27`, `Community 28`, `Community 30`, `Community 31`, `Community 42`, `Community 51`, `Community 58`, `Community 59`, `Community 60`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `AppServices` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`AppServices` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `create_fastapi_app()` (e.g. with `lifespan()` and `SpaEntry`) actually correct?**
  _`create_fastapi_app()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `LibraryFolder` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`LibraryFolder` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `BundledTool` (e.g. with `AfcDeviceRepository` and `device_repository_for()`) actually correct?**
  _`BundledTool` has 25 INFERRED edges - model-reasoned connections that need verification._