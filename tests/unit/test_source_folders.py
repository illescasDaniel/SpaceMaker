from spacemaker.domain.source_folders import SourceFolder, path_matches_source_folders


def test_given_dcim_path_when_dcim_selected_then_matches():
	# given
	selected = frozenset({SourceFolder.DCIM})
	# when / then
	assert path_matches_source_folders("/sdcard/DCIM/photo.jpg", selected)


def test_given_pictures_path_when_only_dcim_selected_then_no_match():
	# given
	selected = frozenset({SourceFolder.DCIM})
	# when / then
	assert not path_matches_source_folders("Pictures/foo.jpg", selected)
