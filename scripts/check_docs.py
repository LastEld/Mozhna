#!/usr/bin/env python3
"""Check repository documents and JSON syntax; no runtime claims or network."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "CONTRIBUTING.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md",
    "CHANGELOG.md", "docs/README.md", "docs/PRODUCT.md", "docs/CONTEXT.md",
    "docs/REQUIREMENTS.md", "docs/ROADMAP.md", "docs/ARCHITECTURE.md",
    "docs/MONEY.md", "docs/DATA_MODEL.md", "docs/INTEGRATIONS.md",
    "docs/ACTIONS.md", "docs/VALIDATION.md", "docs/BACKLOG.md",
    "docs/OPERATIONS.md", "docs/adr/README.md", "apps/web/README.md",
    "docs/STACK.md", "docs/CLOUD_EXECUTION.md", "docs/CLIENTS.md",
    "docs/LLM_ADAPTERS.md", "docs/DEPLOYMENT.md",
    "docs/adr/0008-model-providers.md", "docs/adr/0009-adaptive-clients.md",
    "docs/adr/0010-cloud-execution.md", "infra/render/README.md",
    "infra/docker/README.md",
    "services/backend/README.md", "packages/README.md", "infra/README.md",
    "tests/README.md", "tests/fixtures/money-cases.json",
    ".github/CODEOWNERS", ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/task.yml",
)
EXCLUDED = {".git", "node_modules", ".venv", "dist", "build"}


def check():
    errors = []
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required file: {name}")
    files = [p for p in ROOT.rglob("*") if p.is_file()
             and not (set(p.relative_to(ROOT).parts) & EXCLUDED)]
    markdown = [p for p in files if p.suffix == ".md"]
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if not text.strip() or not text.endswith("\n"):
            errors.append(f"Empty document or missing final newline: {rel}")
        outside_code = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", text)
        for target in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", outside_code):
            target = target.strip().split(' "', 1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f"Broken local link: {rel} -> {target}")
    json_files = [p for p in files if p.suffix == ".json"]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            errors.append(f"Invalid JSON: {path.relative_to(ROOT)}: {exc}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"OK: {len(markdown)} Markdown files, local file links, "
          f"{len(json_files)} JSON file(s), required scaffold.")
    print("Runtime behavior, remote links and Markdown anchors are not checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
