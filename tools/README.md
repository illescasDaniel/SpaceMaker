# CLI tools (managed download folder)

SpaceMaker resolves third-party binaries in this order:

1. **Managed folder** — `~/.local/share/spacemaker/tools` (Linux), or the OS-specific path shown in **Settings**
2. **Download** — pinned builds from the app catalog on first launch
3. **System `PATH`** — only after you choose **Continue** on the components setup screen (or when `SPACEMAKER_DEV=1` for contributors)

Required tool names: `adb`, `ffmpeg`, `ffprobe`, `magick`, `exiftool`, `mtp-detect`, `mtp-getfile`.

Optional override for tests or custom layouts: `SPACEMAKER_TOOLS_DIR=/path/to/tools`.

See [specs/packaging/SPEC.md](../specs/packaging/SPEC.md) and [packaging/tool-catalog.json](../packaging/tool-catalog.json).
