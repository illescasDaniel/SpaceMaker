# Bundled CLI tools (dev + release)

SpaceMaker runs **only** binaries from this directory (`tools/<name>`), not your system `PATH`.

Release builds ship a full `tools/` tree per [packaging/third-party-manifest.yaml](../packaging/third-party-manifest.yaml).

## Local development

1. **Preferred:** copy the same pinned binaries CI uses for your OS/CPU into this folder.
2. **Convenience (dev):** populate symlinks from tools already on `PATH`:

   ```bash
   uv run task dev-tools -- --from-path
   ```

3. **Optional:** set `SPACEMAKER_DEV=1` when running SpaceMaker to allow `PATH` fallback without files here (not recommended; release behavior always uses `tools/`).

Required names on Linux: `adb`, `ffmpeg`, `ffprobe`, `magick`, `exiftool`, `mtp-detect`, `mtp-getfile`.
