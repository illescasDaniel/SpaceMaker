---
name: transfer-download-to-documents-window
description: desktop Transfer Download saves to Documents/SpaceMaker; Home centered, window 960x720
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

Transfer desktop Download saves to Documents/SpaceMaker; Home centered + 960×720.

- **Context:** Desktop Transfer **Download** used `<a download>` which pywebview ignores. User wanted copies in `Documents/SpaceMaker` with visible feedback. Also asked for a smaller default window and a centered Home grid.
- **Decision:** `SaveTransferItemToDocuments` use case + loopback `POST /api/transfer/save`; phone keeps streaming `GET /api/transfer/download`. UI Tip + Open documents folder. Default window `960×720`; `#view-home` flex-centered. Spec/wireframe updated under SDD (redundant session/Documents lead line removed).
- **Rationale:** Documents root already used by Receive; collision suffix matches transfer naming; ephemeral staging unchanged.

HEAD check 2026-11-17: the default window is now 1152x864 (`bootstrap/window_geometry.py`); the 960x720 above is history.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Transfer desktop Download saves to Documents/SpaceMaker; Home centered + 960×720".
