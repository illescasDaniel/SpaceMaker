import io
import subprocess
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.device import adb_repository
from spacemaker.adapters.outbound.device.adb_repository import AdbDeviceRepository
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind


class _FakeRun:
	def __init__(self, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"", timeout: bool = False) -> None:
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr
		self.timeout = timeout
		self.argv: list[str] = []
		self.timeout_s: float | None = None

	def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
		self.argv = argv
		self.timeout_s = kwargs["timeout"]  # type: ignore[assignment]
		if self.timeout:
			raise subprocess.TimeoutExpired(argv, 1)
		out = kwargs["stdout"]
		if isinstance(out, io.BufferedWriter):
			out.write(self.stdout)
			return subprocess.CompletedProcess(argv, self.returncode, None, self.stderr)
		return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


def _repo(monkeypatch: pytest.MonkeyPatch, fake: _FakeRun) -> AdbDeviceRepository:
	monkeypatch.setattr(adb_repository.subprocess, "run", fake)
	return AdbDeviceRepository(Path("/opt/adb"))


def test_given_path_with_quote_when_read_head_then_one_quoted_argument_after_double_dash(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	fake = _FakeRun(stdout=b"\xff\xd8head")
	repo = _repo(monkeypatch, fake)
	# when
	head = repo.read_head("dev1", "DCIM/it's here.jpg", 65536, 10.0)
	# then
	assert head == b"\xff\xd8head"
	assert fake.argv[:5] == ["/opt/adb", "-s", "dev1", "exec-out", fake.argv[4]]
	assert fake.argv[4] == "head -c 65536 -- '/sdcard/DCIM/it'\"'\"'s here.jpg'"
	assert fake.timeout_s == 10.0


@pytest.mark.parametrize(
	("stderr", "kind"),
	[
		(b"head: /sdcard/x.jpg: No such file or directory", DeviceBrowseErrorKind.NOT_FOUND),
		(b"error: device unauthorized.", DeviceBrowseErrorKind.UNAUTHORIZED),
		(b"error: no devices/emulators found", DeviceBrowseErrorKind.UNPLUGGED),
		(b"head: /sdcard/x.jpg: Permission denied", DeviceBrowseErrorKind.PERMISSION_DENIED),
	],
)
def test_given_adb_failure_when_read_head_then_browse_error_kind(
	monkeypatch: pytest.MonkeyPatch, stderr: bytes, kind: DeviceBrowseErrorKind
) -> None:
	# given
	repo = _repo(monkeypatch, _FakeRun(returncode=1, stderr=stderr))
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.read_head("dev1", "x.jpg", 10, 5.0)
	assert exc.value.kind is kind


def test_given_timeout_when_read_head_then_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	repo = _repo(monkeypatch, _FakeRun(timeout=True))
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.read_head("dev1", "x.jpg", 10, 5.0)
	assert exc.value.kind is DeviceBrowseErrorKind.TIMEOUT


def test_given_stat_output_when_stat_file_then_entry_named_after_path(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	fake = _FakeRun(stdout=b"regular file|4096|1760000100|/sdcard/DCIM/Camera/IMG_1.jpg\n")
	repo = _repo(monkeypatch, fake)
	# when
	entry = repo.stat_file("dev1", "DCIM/Camera/IMG_1.jpg")
	# then
	assert (entry.name, entry.is_dir, entry.size, entry.mtime) == ("IMG_1.jpg", False, 4096, 1760000100)
	assert "stat -L -c" in fake.argv[4]


def test_given_missing_file_when_stat_file_then_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	repo = _repo(monkeypatch, _FakeRun(returncode=1, stdout=b"stat: '/sdcard/x': No such file or directory\n"))
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.stat_file("dev1", "x")
	assert exc.value.kind is DeviceBrowseErrorKind.NOT_FOUND


def test_given_file_when_pull_with_timeout_then_streams_cat_to_local_file(
	monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
	# given
	fake = _FakeRun(stdout=b"photo-bytes")
	repo = _repo(monkeypatch, fake)
	dest = tmp_path / "out.jpg"
	# when
	repo.pull_file_with_timeout("dev1", "DCIM/a.jpg", str(dest), 30.0)
	# then
	assert dest.read_bytes() == b"photo-bytes"
	assert fake.argv[4] == "cat -- /sdcard/DCIM/a.jpg"
	assert fake.timeout_s == 30.0


# Video posters: ``read_range`` is one ``adb exec-out dd`` bounded to the range (SPEC "Video posters — strategy").
def test_given_path_with_quote_when_read_range_then_dd_with_skip_count_and_one_quoted_path(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	fake = _FakeRun(stdout=b"range-bytes", stderr=b"1+0 records in\n1+0 records out\n11 bytes copied")
	repo = _repo(monkeypatch, fake)
	# when
	data = repo.read_range("dev1", "DCIM/it's here.mp4", 4_194_304, 4_194_304, 10.0)
	# then
	assert data == b"range-bytes"
	assert fake.argv[:4] == ["/opt/adb", "-s", "dev1", "exec-out"]
	assert fake.argv[4] == (
		"dd if='/sdcard/DCIM/it'\"'\"'s here.mp4' iflag=skip_bytes,count_bytes skip=4194304 count=4194304"
	)
	assert fake.timeout_s == 10.0


@pytest.mark.parametrize(
	("stderr", "kind"),
	[
		(b"dd: /sdcard/x.mp4: No such file or directory", DeviceBrowseErrorKind.NOT_FOUND),
		(b"error: device unauthorized.", DeviceBrowseErrorKind.UNAUTHORIZED),
		(b"error: no devices/emulators found", DeviceBrowseErrorKind.UNPLUGGED),
		(b"dd: /sdcard/x.mp4: Permission denied", DeviceBrowseErrorKind.PERMISSION_DENIED),
	],
)
def test_given_adb_failure_when_read_range_then_browse_error_kind(
	monkeypatch: pytest.MonkeyPatch, stderr: bytes, kind: DeviceBrowseErrorKind
) -> None:
	# given
	repo = _repo(monkeypatch, _FakeRun(returncode=1, stderr=stderr))
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.read_range("dev1", "x.mp4", 0, 10, 5.0)
	assert exc.value.kind is kind


def test_given_timeout_when_read_range_then_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
	# given
	repo = _repo(monkeypatch, _FakeRun(timeout=True))
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.read_range("dev1", "x.mp4", 0, 10, 5.0)
	assert exc.value.kind is DeviceBrowseErrorKind.TIMEOUT
