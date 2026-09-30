from spacemaker.domain.managed_tool import (
	ToolResolution,
	ToolsSummaryStatus,
	summarize_tool_resolutions,
	tools_summary_line,
)


def test_given_any_missing_when_summarize_then_missing():
	# given
	resolutions = [ToolResolution.MANAGED, ToolResolution.MISSING, ToolResolution.PATH]
	# when
	status = summarize_tool_resolutions(resolutions)
	# then
	assert status is ToolsSummaryStatus.MISSING


def test_given_path_without_missing_when_summarize_then_ok():
	# given
	resolutions = [ToolResolution.MANAGED, ToolResolution.PATH]
	# when
	status = summarize_tool_resolutions(resolutions)
	# then
	assert status is ToolsSummaryStatus.OK


def test_given_all_path_when_summarize_then_ok():
	# given
	resolutions = [ToolResolution.PATH, ToolResolution.PATH]
	# when
	status = summarize_tool_resolutions(resolutions)
	# then
	assert status is ToolsSummaryStatus.OK


def test_given_all_managed_when_summarize_then_ok():
	# given
	resolutions = [ToolResolution.MANAGED, ToolResolution.MANAGED]
	# when
	status = summarize_tool_resolutions(resolutions)
	# then
	assert status is ToolsSummaryStatus.OK


def test_given_counts_when_summary_line_then_formatted():
	# given
	managed, path, missing = 3, 2, 1
	# when
	line = tools_summary_line(managed=managed, path=path, missing=missing)
	# then
	assert line == "3 ready · 2 system · 1 missing"
