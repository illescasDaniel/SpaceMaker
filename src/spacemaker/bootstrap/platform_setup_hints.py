from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal, TypedDict, cast


LinuxPackageFamily = Literal["apt", "dnf", "arch"]

_OS_RELEASE_PATH = Path("/etc/os-release")
_UNSET: object = object()


def _as_linux_family(value: LinuxPackageFamily | None | object) -> LinuxPackageFamily | None:
	if value is _UNSET or value is None:
		return None
	if value == "apt" or value == "dnf" or value == "arch":
		return cast(LinuxPackageFamily, value)
	return None


# Display-only Homebrew bootstrap (user runs in their own terminal).
_HOMEBREW_INSTALL_COMMAND = (
	'/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
)


class ToolStatusHintRow(TypedDict, total=False):
	"""Managed-tool snapshot fields used for setup hints and status JSON."""

	tool_id: str
	phase: str
	resolution: str
	path: str | None
	message: str | None
	install_command: str | None


_MACOS_FORMULAS: dict[str, str] = {
	"ffmpeg": "brew install ffmpeg",
	"ffprobe": "brew install ffmpeg",
	"magick": "brew install imagemagick",
	"exiftool": "brew install exiftool",
	"avifenc": "brew install libavif",
	"adb": "brew install android-platform-tools",
}

_MACOS_PACKAGES: dict[str, str] = {
	"ffmpeg": "ffmpeg",
	"ffprobe": "ffmpeg",
	"magick": "imagemagick",
	"exiftool": "exiftool",
	"avifenc": "libavif",
	"adb": "android-platform-tools",
}

_WINDOWS_FORMULAS: dict[str, str] = {
	"ffmpeg": "winget install -e --id Gyan.FFmpeg",
	"ffprobe": "winget install -e --id Gyan.FFmpeg",
	"magick": "winget install -e --id ImageMagick.ImageMagick",
	"exiftool": "winget install -e --id OliverBetz.ExifTool",
	"adb": "winget install -e --id Google.PlatformTools",
}

_LINUX_APT_PACKAGES: dict[str, str] = {
	"ffmpeg": "ffmpeg",
	"ffprobe": "ffmpeg",
	"magick": "imagemagick",
	"exiftool": "libimage-exiftool-perl",
	"avifenc": "libavif-bin",
	"adb": "adb",
	"idevice_id": "libimobiledevice-utils",
	"idevicepair": "libimobiledevice-utils",
	"ideviceinfo": "libimobiledevice-utils",
	"ifuse": "ifuse",
}

_LINUX_DNF_PACKAGES: dict[str, str] = {
	"ffmpeg": "ffmpeg",
	"ffprobe": "ffmpeg",
	"magick": "ImageMagick",
	"exiftool": "perl-Image-ExifTool",
	"avifenc": "libavif",
	"adb": "android-tools",
	"idevice_id": "libimobiledevice",
	"idevicepair": "libimobiledevice",
	"ideviceinfo": "libimobiledevice",
	"ifuse": "ifuse",
}

_LINUX_ARCH_PACKAGES: dict[str, str] = {
	"ffmpeg": "ffmpeg",
	"ffprobe": "ffmpeg",
	"magick": "imagemagick",
	"exiftool": "perl-image-exiftool",
	"avifenc": "libavif",
	"adb": "android-tools",
	"idevice_id": "libimobiledevice",
	"idevicepair": "libimobiledevice",
	"ideviceinfo": "libimobiledevice",
	"ifuse": "ifuse",
	"adbfs": "adbfs-rootless-git",
}


def show_iphone_usb_hint(*, platform: str | None = None) -> bool:
	"""iPhone USB distro-packages banner is Linux-only."""
	return (platform or sys.platform).startswith("linux")


def _parse_os_release(text: str) -> tuple[str, list[str]]:
	values: dict[str, str] = {}
	for raw in text.splitlines():
		line = raw.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, _, value = line.partition("=")
		values[key.strip()] = value.strip().strip('"').strip("'")
	os_id = values.get("ID", "").lower()
	like = values.get("ID_LIKE", "").lower().split()
	return os_id, like


def _family_from_ids(os_id: str, like: list[str]) -> LinuxPackageFamily | None:
	tokens = {os_id, *like}
	if tokens & {"debian", "ubuntu"}:
		return "apt"
	if tokens & {"fedora", "rhel", "centos", "rocky", "almalinux"}:
		return "dnf"
	if tokens & {"arch", "manjaro", "endeavouros"}:
		return "arch"
	return None


def detect_linux_package_family(
	*,
	os_release_text: str | None = None,
	which: Callable[[str], str | None] | None = None,
) -> LinuxPackageFamily | None:
	"""Map this host to apt / dnf / arch, or None when unknown."""
	text = os_release_text
	if text is None and _OS_RELEASE_PATH.is_file():
		try:
			text = _OS_RELEASE_PATH.read_text(encoding="utf-8")
		except OSError:
			text = None
	if text:
		family = _family_from_ids(*_parse_os_release(text))
		if family:
			return family
	probe = which or shutil.which
	if probe("apt-get"):
		return "apt"
	if probe("dnf"):
		return "dnf"
	if probe("pacman"):
		return "arch"
	return None


def arch_install_prefix(*, which: Callable[[str], str | None] | None = None) -> str:
	probe = which or shutil.which
	if probe("paru"):
		return "paru -S"
	if probe("yay"):
		return "yay -S"
	return "sudo pacman -S"


def package_manager_present(
	*,
	platform: str | None = None,
	linux_family: LinuxPackageFamily | None = None,
	which: Callable[[str], str | None] | None = None,
) -> bool:
	"""True when the expected OS package manager binary is on PATH."""
	probe = which or shutil.which
	plat = platform if platform is not None else sys.platform
	if plat == "darwin":
		return probe("brew") is not None
	if plat == "win32":
		return probe("winget") is not None
	if plat.startswith("linux"):
		family = linux_family
		if family is None:
			family = detect_linux_package_family(which=which)
		if family == "apt":
			return probe("apt-get") is not None
		if family == "dnf":
			return probe("dnf") is not None
		if family == "arch":
			return probe("pacman") is not None or probe("paru") is not None or probe("yay") is not None
		return False
	return False


def package_manager_command(
	*,
	platform: str | None = None,
	linux_family: LinuxPackageFamily | None = None,
	which: Callable[[str], str | None] | None = None,
) -> str | None:
	"""Display-only PM install command when the expected manager is missing; else None."""
	if package_manager_present(platform=platform, linux_family=linux_family, which=which):
		return None
	plat = platform if platform is not None else sys.platform
	if plat == "darwin":
		return _HOMEBREW_INSTALL_COMMAND
	# Windows / Linux: no safe one-liner we are sure of — omit the PM step.
	return None


def _tool_needs_install_hint(*, phase: str, resolution: str) -> bool:
	if resolution in {"managed", "path"}:
		return False
	if phase == "downloading":
		return False
	return resolution == "missing" or phase == "failed"


def _linux_command(
	tool_id: str,
	*,
	family: LinuxPackageFamily,
	arch_prefix: str,
) -> str | None:
	if family == "apt":
		pkg = _LINUX_APT_PACKAGES.get(tool_id)
		return f"sudo apt install {pkg}" if pkg else None
	if family == "dnf":
		pkg = _LINUX_DNF_PACKAGES.get(tool_id)
		return f"sudo dnf install {pkg}" if pkg else None
	pkg = _LINUX_ARCH_PACKAGES.get(tool_id)
	if not pkg:
		return None
	return f"{arch_prefix} {pkg}"


def install_command_for_tool(
	tool_id: str,
	*,
	phase: str,
	resolution: str,
	platform: str | None = None,
	linux_family: LinuxPackageFamily | None | object = _UNSET,
	arch_prefix: str | None = None,
	os_release_text: str | None = None,
	which: Callable[[str], str | None] | None = None,
) -> str | None:
	"""Display-only package-manager one-liner for a failed/missing tool, or None."""
	if not _tool_needs_install_hint(phase=phase, resolution=resolution):
		return None
	plat = platform if platform is not None else sys.platform
	if plat == "darwin":
		return _MACOS_FORMULAS.get(tool_id)
	if plat == "win32":
		return _WINDOWS_FORMULAS.get(tool_id)
	if plat.startswith("linux"):
		if linux_family is _UNSET:
			resolved_family = detect_linux_package_family(
				os_release_text=os_release_text,
				which=which,
			)
		else:
			resolved_family = _as_linux_family(linux_family)
		if resolved_family is None:
			return None
		prefix = arch_prefix if arch_prefix is not None else arch_install_prefix(which=which)
		return _linux_command(tool_id, family=resolved_family, arch_prefix=prefix)
	return None


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
	seen: set[str] = set()
	out: list[str] = []
	for item in items:
		if item in seen:
			continue
		seen.add(item)
		out.append(item)
	return out


def install_all_command(
	missing_tool_ids: Iterable[str],
	*,
	platform: str | None = None,
	linux_family: LinuxPackageFamily | None | object = _UNSET,
	arch_prefix: str | None = None,
	os_release_text: str | None = None,
	which: Callable[[str], str | None] | None = None,
) -> str | None:
	"""Combined display-only install for all missing tools (packages deduped), or None."""
	ids = list(missing_tool_ids)
	if not ids:
		return None
	plat = platform if platform is not None else sys.platform
	if plat == "darwin":
		packages = _dedupe_preserve(_MACOS_PACKAGES[tid] for tid in ids if tid in _MACOS_PACKAGES)
		if not packages:
			return None
		return "brew install " + " ".join(packages)
	if plat == "win32":
		lines = _dedupe_preserve(_WINDOWS_FORMULAS[tid] for tid in ids if tid in _WINDOWS_FORMULAS)
		if not lines:
			return None
		return "\n".join(lines)
	if plat.startswith("linux"):
		if linux_family is _UNSET:
			resolved_family = detect_linux_package_family(
				os_release_text=os_release_text,
				which=which,
			)
		else:
			resolved_family = _as_linux_family(linux_family)
		if resolved_family is None:
			return None
		prefix = arch_prefix if arch_prefix is not None else arch_install_prefix(which=which)
		if resolved_family == "apt":
			packages = _dedupe_preserve(_LINUX_APT_PACKAGES[tid] for tid in ids if tid in _LINUX_APT_PACKAGES)
			return f"sudo apt install {' '.join(packages)}" if packages else None
		if resolved_family == "dnf":
			packages = _dedupe_preserve(_LINUX_DNF_PACKAGES[tid] for tid in ids if tid in _LINUX_DNF_PACKAGES)
			return f"sudo dnf install {' '.join(packages)}" if packages else None
		packages = _dedupe_preserve(_LINUX_ARCH_PACKAGES[tid] for tid in ids if tid in _LINUX_ARCH_PACKAGES)
		return f"{prefix} {' '.join(packages)}" if packages else None
	return None
