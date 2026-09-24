# Graph Report - SpaceMaker  (2026-09-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1378 nodes · 3550 edges · 83 communities (66 shown, 17 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 453 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `176db110`
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
- Community 68
- Community 69
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
- Community 82

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
- `test_given_payload_when_encode_qr_svg_then_white_background()` --calls--> `encode_qr_svg()`  [INFERRED]
  tests/unit/test_qr_svg.py → src/spacemaker/adapters/inbound/web/qr_svg.py
- `test_given_file_and_folder_when_build_share_manifest_then_one_row_each()` --calls--> `build_share_manifest()`  [INFERRED]
  tests/unit/test_file_share_manifest.py → src/spacemaker/application/file_share_manifest.py
- `test_given_folder_with_files_when_write_folder_zip_then_preserves_relative_paths()` --calls--> `write_folder_zip()`  [INFERRED]
  tests/unit/test_file_share_manifest.py → src/spacemaker/application/file_share_manifest.py
- `test_given_error_files_when_count_then_warning_visible()` --uses--> `FolderWarnings`  [INFERRED]
  tests/unit/test_wizard.py → src/spacemaker/domain/wizard.py
- `FakeMediaProbe` --uses--> `GalleryDisplayMetadata`  [INFERRED]
  tests/unit/fakes.py → src/spacemaker/domain/gallery_metadata.py

## Import Cycles
- None detected.

## Communities (83 total, 17 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (101): api(), appendThumbCell(), applyConnectionPanels(), applyGalleryExport(), applyGalleryFirewallHints(), applyState(), bindGalleryUi(), bindInfoPanelToggle() (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (51): spacemaker_application_easy_session, spacemaker_application_wizard_state, spacemaker_domain_app_module, spacemaker_domain_convert_policy, spacemaker_domain_jobs, spacemaker_domain_ui_mode, spacemaker_domain_wizard, AppSession (+43 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (48): fastapi_testclient, fixture, log(), run_step(), checks.sh script, lib_find_repo_root(), lib_require_venv(), lib_uv_run() (+40 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (30): create_fastapi_app(), convert_stop(), easy_bootstrap(), extract_pause(), extract_resume(), extract_start(), extract_stop(), extract_upload_qr() (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (14): spacemaker_domain_upload_paths, ErrorRecovery, DocumentUploadDisposition, DocumentUploadOutcome, StrEnum, ReceiveUploadedDocuments, ReceiveUploadedMedia, UploadOutcome (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (22): enum, spacemaker_domain_conversion, ConversionRoute, image_avif_relative_path(), output_exceeds_rollback_threshold(), PlannedOutput, StrEnum, relative_parent_stem() (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (27): useAriaPropsSupportedByRole, useSemanticElements, useArrowFunction, files, includes, formatter, enabled, indentStyle (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (12): spacemaker_application_extract_media, AfcDeviceRepository, apple_usb_plugged(), Path, usbmuxd_running(), Path, test_given_100apple_at_mount_root_when_list_media_paths_then_prefixes_dcim(), test_given_afc_mount_when_extract_dcim_then_copies_to_originals() (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (21): Path, app_icon_path(), bundle_resource_root(), clear_components_setup_complete(), components_setup_complete_marker(), display_user_path(), ensure_managed_tools_dir(), load_components_setup_complete() (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (9): adbutils, os, main(), Offscreen Qt WebEngine smoke test (post-prune AppDir venv)., pathlib, Dispatch quality gate to checks.sh (via bash on Windows)., shutil, skip_library_relative_path() (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (15): spacemaker_application_convert_media, FakeMediaConverter, FakeMediaProbe, test_given_stop_after_first_file_when_convert_then_stops_early(), _paths(), test_given_avif_in_originals_when_convert_then_moves_to_converted(), test_given_encode_fails_twice_when_convert_then_moves_to_error(), test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs() (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (13): ExportFriendlyMedia, ExportResult, export_cache_filename(), ExportFormat, ExportJobPhase, is_friendly_h264_aac_mp4(), is_friendly_jpeg_filename(), StrEnum (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (9): spacemaker_application_delete_gallery_item, LocalFileSystem, DeleteGalleryItem, LibraryFolder, test_given_converted_file_when_delete_then_removed_and_thumb_cleared(), test_given_missing_file_when_delete_then_false(), Path, test_given_nested_files_when_list_and_count_then_match() (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (19): argparse, contextlib, _apply_native_style(), install_qt_native_style(), setup_app(), Apply a platform-appropriate QStyle so pywebview's own QtWidgets dialogs (close…, install_qt_webengine_gpu_flags(), Windows: work around a black/frozen WebEngine surface that only repaints when… (+11 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (19): FastAPI, ipaddress, spacemaker_adapters_inbound_web_client_access, no_cache_shell_assets(), websocket_endpoint(), is_loopback_client_host(), require_loopback_websocket(), starlette_requests (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (20): BundledTool, _executable_file(), missing_bundled_tools(), Path, StrEnum, Return (path, source) where source is 'managed' or 'path'., ImageMagick winget/installer often lands under Program Files without updating…, resolve_tool_path() (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (14): GenerateGallery, datetime, days_in_month(), days_with_media(), gallery_item(), GalleryItem, group_timeline(), items_for_day() (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (8): dataclasses, GalleryItemDetail, GetGalleryItem, datetime, GalleryDisplayMetadata, MediaProbePort, datetime, Protocol

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (7): spacemaker_application_receive_uploaded_media, StrEnum, UploadDisposition, FakeFileSystem, Path, test_given_existing_same_size_when_wifi_upload_then_skipped(), test_given_new_file_when_wifi_upload_then_saved()

### Community 20 - "Community 20"
Cohesion: 0.28
Nodes (7): ConvertMedia, count_image_files_in_library_folder(), media_kind_for_extension(), media_kind_for_filename(), MediaKind, normalize_extension(), StrEnum

### Community 21 - "Community 21"
Cohesion: 0.28
Nodes (5): CatalogToolInstaller, Any, Path, bundled_tool_path(), ToolInstallResult

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (9): ManagedToolsService, True when a catalog tool is not yet present in the managed folder (PATH…, is_dev_mode(), managed_tool_present(), tools_install_root(), ManagedToolStatus, StrEnum, ToolInstallPhase (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (18): asyncio, BaseModel, fastapi_responses, fastapi_staticfiles, pydantic, _attachment_named(), open_documents_folder(), share_download() (+10 more)

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (15): socket, server_info(), _firewalld_port_open(), FirewallStatus, _lan_connect_probe(), probe_gallery_port(), _try_tcp_connect(), _ufw_config_enabled() (+7 more)

### Community 25 - "Community 25"
Cohesion: 0.20
Nodes (13): spacemaker_adapters_outbound_media_ffmpeg_encoders, av1_encoder_ffmpeg_args(), h264_hw_encoder_ffmpeg_args(), hardware_video_encoder_from_ffmpeg_encoders(), extract_raw_embedded_jpeg(), Path, HardwareVideoEncoder, StrEnum (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.22
Nodes (17): logging, _delete_top_level_widgets(), _disconnect_signal(), _disconnect_webengine_bindings(), _drain_qt_events(), finalize_qt_after_webview(), install_qt_webengine_shutdown_fix(), close_event() (+9 more)

### Community 27 - "Community 27"
Cohesion: 0.21
Nodes (16): spacemaker_adapters_inbound_web_spa_entry, gallery_page(), root_page(), _spa_file(), is_loopback_host(), is_private_lan_host(), normalize_host(), StrEnum (+8 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (13): spacemaker_application_error_recovery, spacemaker_application_export_friendly_media, spacemaker_domain_gallery_export, spacemaker_domain_gallery_metadata, spacemaker_domain_library, spacemaker_domain_video_encode, spacemaker_domain_web_compat, spacemaker_ports_outbound_device_repository (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.21
Nodes (11): DesktopApi, convert_start(), defaults(), put_settings(), default_library_root(), normalize_library_root(), pictures_directory(), If the user picked a bucket folder (e.g. …/originals), use the library root… (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (13): concurrent_futures, secrets, build_share_manifest(), dedupe_share_selection_paths(), EmptyShareSelectionError, User selection resolves to zero shareable files., Keep first occurrence of each top-level path (compared by resolved absolute…, One manifest row per top-level selected path (file or folder zip). (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (12): hashlib, io, json, segno, catalog_path(), load_platform_catalog(), Any, Path (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.20
Nodes (11): spacemaker_application_managed_tools, spacemaker_domain_managed_tool, spacemaker_ports_outbound_tool_installer, FakeInstaller, Path, test_given_catalog_installs_when_ensure_then_places_file(), fake_install(), test_given_continue_marker_on_disk_when_new_service_then_setup_not_pending() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.21
Nodes (4): raw_embedded_preview_available(), datetime, SubprocessMediaProbe, is_raw_extension()

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (6): ExtractMedia, JobProgress, StrEnum, TransferMode, DeviceRepositoryPort, Protocol

### Community 35 - "Community 35"
Cohesion: 0.27
Nodes (7): CompletedProcess, RuntimeError, Path, ToolExecutionError, ToolRunner, bundle_root(), is_frozen()

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (13): Popen, _bypass_components_setup(), _ephemeral_port(), main(), _prepare_smoke_home(), Path, Capture the SpaceMaker Home hub for README (offscreen Qt WebEngine)., _server_env() (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (11): spacemaker_adapters_outbound_device_adb_repository, spacemaker_adapters_outbound_device_afc_repository, spacemaker_adapters_outbound_device_factory, spacemaker_adapters_outbound_device_mtp_repository, spacemaker_domain_connection, device_repository_for(), ConnectionMethod, StrEnum (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.14
Nodes (4): spacemaker_domain_extract_control, ExtractJobControl, test_given_pause_requested_when_after_file_then_marked_paused(), test_given_stop_requested_when_before_next_file_then_aborts_queue()

### Community 39 - "Community 39"
Cohesion: 0.22
Nodes (10): Path, Guards against Cursor/Claude Code agent-context drift and re-bloat. AGENTS.md…, Split a `---`-delimited YAML frontmatter block from the body below it., _rule_pairs(), _split_frontmatter(), test_given_a_rule_pair_when_comparing_bodies_then_they_are_byte_identical(), test_given_a_rule_pair_when_comparing_scoping_then_always_apply_and_globs_are_equivalent(), test_given_cursor_rules_dir_when_listing_pairs_then_every_cursor_rule_has_a_claude_counterpart() (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (12): spacemaker_adapters_outbound_media_subprocess_converter, spacemaker_adapters_outbound_media_subprocess_probe, spacemaker_adapters_outbound_media_tool_runner, _install_tool_scripts(), Path, _skip_on_windows, test_given_dng_when_magick_cannot_read_then_converts_embedded_preview(), MonkeyPatch (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (4): on_progress(), Protocol, WebSocketLike, GalleryExportJob

### Community 44 - "Community 44"
Cohesion: 0.26
Nodes (5): DeviceInfo, FakeDeviceRepository, test_given_copy_mode_when_extract_then_file_stays_on_device(), test_given_existing_original_with_same_size_when_extract_then_skips_pull(), test_given_thumbnails_path_when_extract_then_skips_pull()

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (9): datetime, spacemaker_application_generate_gallery, spacemaker_application_get_gallery_item, spacemaker_domain_gallery, spacemaker_domain_media, test_given_converted_and_originals_when_calendar_days_then_converted_only(), test_given_converted_files_when_generate_then_lists_only_converted(), test_given_converted_file_when_get_item_then_returns_detail() (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.20
Nodes (11): gallery_calendar(), gallery_day(), gallery_item_delete(), gallery_item_detail(), gallery_timeline(), library_counts(), _gallery_item_dict(), _metadata_dict() (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (10): devDependencies, @biomejs/biome, @fortawesome/fontawesome-free, name, private, scripts, check, fix (+2 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (10): spacemaker_application_file_share_manifest, count_shareable_files_in_root(), prune_share_selection_paths(), Count regular files under a share root (file itself or directory tree)., Drop folder paths with zero files. Returns (kept paths, had_empty_folder)., test_given_empty_folder_path_when_prune_share_selection_then_dropped(), test_given_empty_folder_when_count_shareable_files_then_zero(), test_given_file_and_folder_when_build_share_manifest_then_one_row_each() (+2 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (4): spacemaker_application_receive_uploaded_documents, FakeFs, Path, test_given_valid_relative_path_when_ingest_then_saved_under_dest_root()

### Community 51 - "Community 51"
Cohesion: 0.24
Nodes (3): AdbDevice, AdbDeviceRepository, Path

### Community 52 - "Community 52"
Cohesion: 0.24
Nodes (10): FileResponse, _attachment_filename(), gallery_export_file(), gallery_export_start(), media_file(), thumb_file(), _no_cache_file(), _path_is_under_base() (+2 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (6): Image, pil, main(), Path, Regenerate app icon + favicon PNGs from packaging/assets/spacemaker-icon-…, _save_resize()

### Community 55 - "Community 55"
Cohesion: 0.24
Nodes (6): is_path_under_roots(), Path, Write folder contents to dest, preserving relative paths inside the archive., ShareDownloadTarget, write_folder_zip(), Path

### Community 56 - "Community 56"
Cohesion: 0.28
Nodes (6): collections_abc, spacemaker_domain_library_paths, True for device or library paths under skipped folders (e.g. .thumbnails)., skip_media_path(), test_given_normal_path_when_skip_media_path_then_false(), test_given_thumbnails_in_device_path_when_skip_media_path_then_true()

### Community 57 - "Community 57"
Cohesion: 0.33
Nodes (6): importlib_metadata, app_release_info(), app_version(), Release identity (mirrors [project] in pyproject.toml)., SpaceMaker — local media backup, convert, and gallery., test_given_installed_package_when_reading_release_info_then_matches_1_0()

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (4): spacemaker_adapters_outbound_filesystem_local, Path, RecordingConverter, test_given_nested_original_when_convert_then_creates_converted_parent()

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (4): spacemaker_adapters_outbound_tools_catalog_installer, Path, test_given_zip_flatten_when_install_then_places_exiftool_tree(), ZipFile

### Community 60 - "Community 60"
Cohesion: 0.36
Nodes (7): spacemaker_domain_source_folders, parse_source_folders(), path_matches_source_folders(), StrEnum, SourceFolder, test_given_dcim_path_when_dcim_selected_then_matches(), test_given_pictures_path_when_only_dcim_selected_then_no_match()

### Community 61 - "Community 61"
Cohesion: 0.46
Nodes (7): convert_to_av1(), convert_to_avif(), detect_encoder(), get_bitrate_bps(), is_browser_compatible(), process_file(), convert_all_1_1.sh script

### Community 62 - "Community 62"
Cohesion: 0.32
Nodes (7): httpx, _free_port(), Launches the real `spacemaker` process (not TestClient) to catch startup bugs…, _read_output_into(), test_given_real_process_when_server_only_starts_then_boots_and_serves(), threading, time

### Community 64 - "Community 64"
Cohesion: 0.29
Nodes (6): APPDIR, QT_QPA_PLATFORM, build-appdir.sh script, SPACEMAKER_BUNDLE_ROOT, UV_LINK_MODE, UV_PYTHON_PREFERENCE

### Community 65 - "Community 65"
Cohesion: 0.29
Nodes (5): APPIMAGE_EXTRACT_AND_RUN, HOME, PATH, QT_QPA_PLATFORM, smoke-appimage.sh script

### Community 66 - "Community 66"
Cohesion: 0.52
Nodes (6): spacemaker_adapters_outbound_media_raw_preview, Path, _skip_on_windows, test_given_exiftool_has_preview_when_available_then_true(), test_given_preview_bytes_when_extract_then_writes_jpeg(), _write_fake_exiftool()

### Community 68 - "Community 68"
Cohesion: 0.29
Nodes (3): Protocol, Download and place one tool into the managed tools directory., ToolInstallerPort

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (6): _capture_with_webengine(), fail(), on_load_ok(), poll_home(), on_result(), save_png()

### Community 73 - "Community 73"
Cohesion: 0.60
Nodes (4): components_setup_hint(), Any, Optional copy + install command for the Components setup screen., _windows_winget_ids()

### Community 74 - "Community 74"
Cohesion: 0.83
Nodes (3): keep_binding(), rm_rf(), prune_pyqt6.sh script

### Community 75 - "Community 75"
Cohesion: 0.67
Nodes (3): re, _manifest_ids(), test_given_manifest_when_compare_to_bundled_tool_enum_then_ids_match()

## Knowledge Gaps
- **41 isolated node(s):** `PlannedOutput`, `web.sh script`, `@biomejs/biome`, `@fortawesome/fontawesome-free`, `name` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 300 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppServices` connect `Community 6` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 12`, `Community 13`, `Community 16`, `Community 17`, `Community 18`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 25`, `Community 30`, `Community 33`, `Community 34`, `Community 35`, `Community 37`, `Community 38`, `Community 42`, `Community 43`, `Community 46`, `Community 50`, `Community 52`, `Community 55`, `Community 60`, `Community 63`, `Community 67`, `Community 70`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `create_fastapi_app()` connect `Community 3` to `Community 1`, `Community 34`, `Community 2`, `Community 37`, `Community 6`, `Community 12`, `Community 13`, `Community 46`, `Community 15`, `Community 52`, `Community 23`, `Community 24`, `Community 57`, `Community 27`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `LibraryFolder` connect `Community 13` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 11`, `Community 12`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 23`, `Community 28`, `Community 30`, `Community 34`, `Community 40`, `Community 44`, `Community 45`, `Community 52`, `Community 56`, `Community 58`, `Community 63`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `AppServices` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`AppServices` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `create_fastapi_app()` (e.g. with `lifespan()` and `SpaEntry`) actually correct?**
  _`create_fastapi_app()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `LibraryFolder` (e.g. with `create_fastapi_app()` and `_resolve_converted_file()`) actually correct?**
  _`LibraryFolder` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `BundledTool` (e.g. with `AfcDeviceRepository` and `device_repository_for()`) actually correct?**
  _`BundledTool` has 25 INFERRED edges - model-reasoned connections that need verification._