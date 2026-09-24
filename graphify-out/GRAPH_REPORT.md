# Graph Report - graphrag-mkdocs-codebase-graph-891193  (2026-09-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1338 nodes · 3490 edges · 74 communities (61 shown, 13 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 451 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `856dbc1e`
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
- Community 71
- Community 72
- Community 73

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
- `test_given_stop_after_first_file_when_convert_then_stops_early()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media_control.py → src/spacemaker/application/convert_media.py
- `test_given_avif_in_originals_when_convert_then_moves_to_converted()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media.py → src/spacemaker/application/convert_media.py
- `test_given_encode_fails_twice_when_convert_then_moves_to_error()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media.py → src/spacemaker/application/convert_media.py
- `test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media.py → src/spacemaker/application/convert_media.py
- `test_given_low_bitrate_mp4_when_convert_then_move_as_is()` --uses--> `ConvertMedia`  [INFERRED]
  tests/unit/test_convert_media.py → src/spacemaker/application/convert_media.py

## Import Cycles
- None detected.

## Communities (74 total, 13 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (101): api(), appendThumbCell(), applyConnectionPanels(), applyGalleryExport(), applyGalleryFirewallHints(), applyState(), bindGalleryUi(), bindInfoPanelToggle() (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (50): collections_abc, spacemaker_domain_conversion, ConvertMedia, ExportFriendlyMedia, ExportResult, GalleryItemDetail, GetGalleryItem, datetime (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (62): concurrent_futures, enum, secrets, spacemaker_adapters_outbound_device_adb_repository, spacemaker_adapters_outbound_device_afc_repository, spacemaker_adapters_outbound_device_factory, spacemaker_adapters_outbound_device_mtp_repository, spacemaker_application_easy_session (+54 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (30): dataclasses, spacemaker_domain_upload_paths, DeleteGalleryItem, ErrorRecovery, GenerateGallery, datetime, DocumentUploadDisposition, DocumentUploadOutcome (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (20): hashlib, json, spacemaker_adapters_outbound_tools_catalog_installer, catalog_path(), CatalogToolInstaller, Any, Path, load_platform_catalog() (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (27): create_fastapi_app(), convert_start(), convert_stop(), easy_bootstrap(), extract_pause(), extract_resume(), extract_start(), extract_stop() (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (15): adbutils, os, main(), Offscreen Qt WebEngine smoke test (post-prune AppDir venv)., pathlib, Dispatch quality gate to checks.sh (via bash on Windows)., shutil, spacemaker_domain_library_paths (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (25): bundle_root(), bundled_tool_path(), BundledTool, _executable_file(), is_dev_mode(), managed_tool_present(), missing_bundled_tools(), Path (+17 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (27): useAriaPropsSupportedByRole, useSemanticElements, useArrowFunction, files, includes, formatter, enabled, indentStyle (+19 more)

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (12): spacemaker_adapters_outbound_media_ffmpeg_encoders, av1_encoder_ffmpeg_args(), h264_hw_encoder_ffmpeg_args(), hardware_video_encoder_from_ffmpeg_encoders(), Path, SubprocessMediaConverter, HardwareVideoEncoder, StrEnum (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (3): AbstractEventLoop, AppServices, datetime

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (16): spacemaker_adapters_outbound_filesystem_local, spacemaker_application_convert_media, spacemaker_application_export_friendly_media, spacemaker_application_get_gallery_item, spacemaker_domain_gallery_export, spacemaker_domain_gallery_metadata, spacemaker_domain_library, spacemaker_domain_video_encode (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (24): fastapi_testclient, create_app(), test_given_adb_without_bundled_tool_when_list_devices_then_503_json(), test_given_app_when_get_qr_svg_then_svg(), test_given_converted_file_when_delete_item_then_removed(), test_given_converted_file_when_gallery_item_api_then_metadata(), test_given_converted_file_when_open_on_host_then_ok(), test_given_converted_files_when_get_settings_then_visualize_ready() (+16 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (22): argparse, httpx, Popen, _bypass_components_setup(), _capture_with_webengine(), fail(), on_load_ok(), poll_home() (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (23): asyncio, BaseModel, fastapi_responses, fastapi_staticfiles, FileResponse, pydantic, _attachment_filename(), _attachment_named() (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (8): spacemaker_application_delete_gallery_item, LocalFileSystem, LibraryFolder, test_given_converted_file_when_delete_then_removed_and_thumb_cleared(), test_given_missing_file_when_delete_then_false(), Path, test_given_nested_files_when_list_and_count_then_match(), test_given_thumbnails_folder_when_list_originals_then_skipped()

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (21): spacemaker_application_file_share_manifest, build_share_manifest(), count_shareable_files_in_root(), dedupe_share_selection_paths(), is_path_under_roots(), prune_share_selection_paths(), Path, Write folder contents to dest, preserving relative paths inside the archive. (+13 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (9): re, extract_raw_embedded_jpeg(), Path, raw_embedded_preview_available(), datetime, SubprocessMediaProbe, is_raw_extension(), _manifest_ids() (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (18): FastAPI, spacemaker_adapters_inbound_web_client_access, no_cache_shell_assets(), websocket_endpoint(), is_loopback_client_host(), require_loopback_websocket(), starlette_requests, starlette_websockets (+10 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (16): socket, gallery_qr(), server_info(), _firewalld_port_open(), FirewallStatus, _lan_connect_probe(), probe_gallery_port(), _try_tcp_connect() (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (18): contextlib, logging, _delete_top_level_widgets(), _disconnect_signal(), _disconnect_webengine_bindings(), _drain_qt_events(), finalize_qt_after_webview(), install_qt_webengine_shutdown_fix() (+10 more)

### Community 21 - "Community 21"
Cohesion: 0.19
Nodes (17): ipaddress, spacemaker_adapters_inbound_web_spa_entry, gallery_page(), root_page(), _spa_file(), is_loopback_host(), is_private_lan_host(), normalize_host() (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (8): spacemaker_ports_outbound_device_repository, ExtractMedia, StrEnum, TransferMode, FakeDeviceRepository, test_given_copy_mode_when_extract_then_file_stays_on_device(), test_given_existing_original_with_same_size_when_extract_then_skips_pull(), test_given_thumbnails_path_when_extract_then_skips_pull()

### Community 23 - "Community 23"
Cohesion: 0.22
Nodes (4): AfcDeviceRepository, apple_usb_plugged(), Path, usbmuxd_running()

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (7): ManagedToolsService, Path, True when a catalog tool is not yet present in the managed folder (PATH…, ManagedToolStatus, StrEnum, ToolInstallPhase, ToolResolution

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (12): FakeMediaConverter, _paths(), test_given_avif_in_originals_when_convert_then_moves_to_converted(), test_given_encode_fails_twice_when_convert_then_moves_to_error(), test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs(), test_given_low_bitrate_mp4_when_convert_then_move_as_is(), test_given_pdf_in_originals_when_convert_then_moves_to_invalid(), test_given_png_when_encode_valid_then_removes_original() (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.26
Nodes (14): clear_components_setup_complete(), components_setup_complete_marker(), default_documents_receive_root(), display_user_path(), documents_directory(), documents_folder_open_target(), ensure_managed_tools_dir(), load_components_setup_complete() (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (11): spacemaker_application_managed_tools, spacemaker_domain_managed_tool, spacemaker_ports_outbound_tool_installer, FakeInstaller, Path, test_given_catalog_installs_when_ensure_then_places_file(), fake_install(), test_given_continue_marker_on_disk_when_new_service_then_setup_not_pending() (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.23
Nodes (10): DesktopApi, defaults(), default_library_root(), normalize_library_root(), pictures_directory(), If the user picked a bucket folder (e.g. …/originals), use the library root…, Path, test_given_library_root_when_normalize_then_unchanged() (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (3): on_progress(), on_progress(), on_progress()

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (4): spacemaker_application_error_recovery, FakeFileSystem, test_given_error_files_when_move_all_to_converted_then_empties_error(), test_given_error_files_when_count_then_warning_visible()

### Community 31 - "Community 31"
Cohesion: 0.14
Nodes (4): spacemaker_domain_extract_control, ExtractJobControl, test_given_pause_requested_when_after_file_then_marked_paused(), test_given_stop_requested_when_before_next_file_then_aborts_queue()

### Community 32 - "Community 32"
Cohesion: 0.28
Nodes (3): MtpDeviceRepository, Path, DeviceInfo

### Community 33 - "Community 33"
Cohesion: 0.30
Nodes (6): CompletedProcess, RuntimeError, Path, ToolExecutionError, ToolRunner, is_frozen()

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (12): spacemaker_adapters_outbound_media_subprocess_converter, spacemaker_adapters_outbound_media_subprocess_probe, spacemaker_adapters_outbound_media_tool_runner, _install_tool_scripts(), Path, _skip_on_windows, test_given_dng_when_magick_cannot_read_then_converts_embedded_preview(), MonkeyPatch (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.23
Nodes (12): app_icon_path(), PNG used for the desktop window / task switcher (dev tree + PyInstaller bundle)., webengine_storage_path(), _apply_qt_window_icon(), main(), on_closing(), _port_in_use(), run_server() (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.26
Nodes (8): lib_find_repo_root(), lib_require_venv(), lib_uv_run(), lib.sh script, pytest.sh script, ruff.sh script, ty.sh script, web.sh script

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (11): gallery_calendar(), gallery_day(), gallery_item_delete(), gallery_item_detail(), gallery_timeline(), library_counts(), _gallery_item_dict(), _metadata_dict() (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.23
Nodes (5): convert_start_policy(), ConvertStartPolicy, StrEnum, test_given_advanced_mode_when_convert_start_policy_then_stop_extract(), test_given_easy_mode_when_convert_start_policy_then_concurrent()

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (9): io, segno, spacemaker_adapters_inbound_web_qr_svg, extract_upload_qr(), receive_qr(), share_qr(), encode_qr_svg(), SVG QR with opaque white background (readable on dark UI themes). (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.18
Nodes (10): devDependencies, @biomejs/biome, @fortawesome/fontawesome-free, name, private, scripts, check, fix (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (4): spacemaker_application_receive_uploaded_documents, FakeFs, Path, test_given_valid_relative_path_when_ingest_then_saved_under_dest_root()

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (6): bundle_resource_root(), Linux AppImage / AppDir share tree (legal, tool catalog, icon)., repo_root(), Path, Contract tests for Linux AppImage / AppDir packaging (no full AppImage build)., test_given_bundle_env_when_resolving_repo_root_then_uses_share_tree()

### Community 43 - "Community 43"
Cohesion: 0.24
Nodes (3): AdbDevice, AdbDeviceRepository, Path

### Community 44 - "Community 44"
Cohesion: 0.22
Nodes (6): Image, pil, main(), Path, Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-…, _save_resize()

### Community 45 - "Community 45"
Cohesion: 0.31
Nodes (9): spacemaker_application_extract_media, spacemaker_domain_source_folders, Path, test_given_100apple_at_mount_root_when_list_media_paths_then_prefixes_dcim(), test_given_afc_mount_when_extract_dcim_then_copies_to_originals(), test_given_dcim_heic_when_list_media_paths_then_lists_relative(), test_given_file_when_pull_and_size_then_match(), test_given_move_when_delete_device_file_then_removes_source() (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (3): EmptyShareSelectionError, User selection resolves to zero shareable files., ValueError

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): importlib_metadata, app_release_info(), app_version(), Release identity (mirrors [project] in pyproject.toml)., SpaceMaker — local media backup, convert, and gallery., test_given_installed_package_when_reading_release_info_then_matches_1_0()

### Community 49 - "Community 49"
Cohesion: 0.42
Nodes (6): parse_source_folders(), path_matches_source_folders(), StrEnum, SourceFolder, test_given_dcim_path_when_dcim_selected_then_matches(), test_given_pictures_path_when_only_dcim_selected_then_no_match()

### Community 50 - "Community 50"
Cohesion: 0.32
Nodes (6): datetime, spacemaker_application_generate_gallery, spacemaker_domain_gallery, spacemaker_domain_media, test_given_converted_and_originals_when_calendar_days_then_converted_only(), test_given_converted_files_when_generate_then_lists_only_converted()

### Community 51 - "Community 51"
Cohesion: 0.46
Nodes (7): convert_to_av1(), convert_to_avif(), detect_encoder(), get_bitrate_bps(), is_browser_compatible(), process_file(), convert_all_1_1.sh script

### Community 52 - "Community 52"
Cohesion: 0.36
Nodes (6): spacemaker_adapters_outbound_host, MonkeyPatch, Path, test_given_directory_when_reveal_in_file_manager_on_linux_then_xdg_opens_that_directory(), fake_run(), test_given_file_when_reveal_in_file_manager_on_linux_then_xdg_opens_parent_directory()

### Community 55 - "Community 55"
Cohesion: 0.29
Nodes (6): APPDIR, QT_QPA_PLATFORM, build-appdir.sh script, SPACEMAKER_BUNDLE_ROOT, UV_LINK_MODE, UV_PYTHON_PREFERENCE

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (5): APPIMAGE_EXTRACT_AND_RUN, HOME, PATH, QT_QPA_PLATFORM, smoke-appimage.sh script

### Community 57 - "Community 57"
Cohesion: 0.52
Nodes (6): spacemaker_adapters_outbound_media_raw_preview, Path, _skip_on_windows, test_given_exiftool_has_preview_when_available_then_true(), test_given_preview_bytes_when_extract_then_writes_jpeg(), _write_fake_exiftool()

### Community 58 - "Community 58"
Cohesion: 0.38
Nodes (6): spacemaker_application_receive_uploaded_media, StrEnum, UploadDisposition, Path, test_given_existing_same_size_when_wifi_upload_then_skipped(), test_given_new_file_when_wifi_upload_then_saved()

### Community 61 - "Community 61"
Cohesion: 0.43
Nodes (5): starlette_testclient, _lan_client_app(), test_given_lan_client_when_gallery_timeline_then_200_if_session_has_library(), test_given_lan_client_when_get_settings_then_403(), test_given_lan_client_when_put_settings_then_403()

### Community 62 - "Community 62"
Cohesion: 0.29
Nodes (3): Path, RecordingConverter, test_given_nested_original_when_convert_then_creates_converted_parent()

### Community 63 - "Community 63"
Cohesion: 0.60
Nodes (4): components_setup_hint(), Any, Optional copy + install command for the Components setup screen., _windows_winget_ids()

### Community 65 - "Community 65"
Cohesion: 0.83
Nodes (3): keep_binding(), rm_rf(), prune_pyqt6.sh script

### Community 66 - "Community 66"
Cohesion: 0.83
Nodes (3): log(), run_step(), checks.sh script

## Knowledge Gaps
- **41 isolated node(s):** `PlannedOutput`, `web.sh script`, `@biomejs/biome`, `@fortawesome/fontawesome-free`, `name` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 283 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppServices` connect `Community 10` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 12`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 22`, `Community 24`, `Community 28`, `Community 29`, `Community 31`, `Community 33`, `Community 37`, `Community 38`, `Community 46`, `Community 47`, `Community 49`, `Community 53`, `Community 59`, `Community 68`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `create_fastapi_app()` connect `Community 5` to `Community 1`, `Community 2`, `Community 37`, `Community 38`, `Community 39`, `Community 10`, `Community 12`, `Community 14`, `Community 47`, `Community 48`, `Community 15`, `Community 18`, `Community 19`, `Community 21`, `Community 22`, `Community 26`, `Community 28`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `LibraryFolder` connect `Community 15` to `Community 1`, `Community 2`, `Community 3`, `Community 34`, `Community 5`, `Community 6`, `Community 10`, `Community 11`, `Community 45`, `Community 14`, `Community 49`, `Community 50`, `Community 53`, `Community 22`, `Community 62`, `Community 25`, `Community 58`, `Community 30`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `AppServices` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`AppServices` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `create_fastapi_app()` (e.g. with `lifespan()` and `SpaEntry`) actually correct?**
  _`create_fastapi_app()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `LibraryFolder` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`LibraryFolder` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `BundledTool` (e.g. with `AfcDeviceRepository` and `device_repository_for()`) actually correct?**
  _`BundledTool` has 25 INFERRED edges - model-reasoned connections that need verification._