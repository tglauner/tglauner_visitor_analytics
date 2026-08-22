# Agent Status Slide

This folder is used by `scripts/status_slide.py`.

Generated status files are ignored by git:

- `status_slide.tex`
- `status_slide.pdf`
- `status_slide_state.json`
- LaTeX build byproducts

Every Codex prompt must open the dark `Status: Working` Beamer PDF in VS Code
and replace it with `Status: Success` or `Status: Issue` before the final
response. GitHub Copilot does not run this Codex-specific lifecycle. The Codex
project hooks call the script at prompt submit and turn stop. The stop hook
preserves an existing final slide and creates a fallback Issue slide only when
Codex ends a turn without recording a final status.
