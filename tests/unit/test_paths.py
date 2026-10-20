import sys
from pathlib import Path

import pytest

from spacemaker.bootstrap.paths import (
	default_library_root,
	device_preview_cache_dir,
	documents_directory,
	normalize_library_root,
)


def test_given_originals_folder_when_normalize_then_parent_library_root(tmp_path: Path) -> None:
	library = tmp_path / "SpaceMakerLibrary"
	originals = library / "originals"
	originals.mkdir(parents=True)
	(originals / "photo.jpg").write_bytes(b"x")

	normalized = normalize_library_root(str(originals))

	assert normalized == str(library.resolve())
	assert (Path(normalized) / "originals" / "photo.jpg").is_file()


def test_given_library_root_when_normalize_then_unchanged(tmp_path: Path) -> None:
	library = tmp_path / "SpaceMakerLibrary"
	library.mkdir()
	assert normalize_library_root(str(library)) == str(library.resolve())


def test_given_xdg_cache_home_when_preview_cache_dir_then_under_it_and_not_under_library(
	tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	# given
	cache_home = tmp_path / "xdg-cache"
	monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
	monkeypatch.setattr(sys, "platform", "linux")
	# when
	cache_dir = device_preview_cache_dir()
	# then
	assert cache_dir.is_relative_to(cache_home)
	assert not cache_dir.is_relative_to(Path(default_library_root()))
	assert not cache_dir.is_relative_to(documents_directory())
