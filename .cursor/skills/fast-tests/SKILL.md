---
name: fast-tests
description: Write fast pytest tests for SpaceMaker (srxy-style given/when/then). Use when creating tests or reviewing test speed and structure.
---

# Fast Tests Skill

See `docs/playbooks/fast-tests.md`.

## Quick rules

- Function names: `test_given_…_when_…_then_…`
- Body sections: `# given`, `# when`, `# then`
- Unit tests use fake ports; no real ffmpeg/adb
- Filesystem: `tmp_path` with `originals/`, `converted/`, `error/`, `invalid/` layout
- Test conversion routing (move-as-is, encode success, retry→error, invalid) at use-case level with mocked `MediaConverter`

## Example port fake

```python
class FakeMediaConverter:
	def encode_image(self, source, dest): ...
```

Inject into `ConvertMedia` use case; assert folder moves and retry policy without subprocess.
