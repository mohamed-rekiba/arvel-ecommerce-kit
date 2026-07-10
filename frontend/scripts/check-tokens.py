#!/usr/bin/env python3
"""Token-completeness check (K1 handoff, Check 1): the custom-property names defined in
src/styles/tokens.css must exactly equal the token names documented in DESIGN.md §2 (the
token catalog). No orphan (defined, undocumented); no doc-only (documented, undefined).
Run: python3 frontend/scripts/check-tokens.py — exits 1 on any mismatch."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TOKENS_CSS = ROOT / "src" / "styles" / "tokens.css"
DESIGN_MD = ROOT / "DESIGN.md"

# --bp-sm / --bp-lg are names in a comment only (no preprocessor) — never real custom
# properties and must never appear in the doc's token catalog either.
EXCLUDED = {"--bp-sm", "--bp-lg"}


def css_token_names() -> set[str]:
    text = TOKENS_CSS.read_text()
    names = {m.group(1) for m in re.finditer(r"^\s*(--[a-z0-9-]+)\s*:", text, re.MULTILINE)}
    return names - EXCLUDED


def doc_token_names() -> set[str]:
    text = DESIGN_MD.read_text()
    start = text.index("## 2. Token catalog")
    end = text.index("\n## 3", start)
    section = text[start:end]
    names: set[str] = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        names.update(m.group(1) for m in re.finditer(r"`(--[a-zA-Z0-9-]+)`", line))
    return names - EXCLUDED


def main() -> int:
    css_names = css_token_names()
    doc_names = doc_token_names()
    orphan_in_css = sorted(css_names - doc_names)
    doc_only = sorted(doc_names - css_names)

    print(f"tokens.css: {len(css_names)} unique token names")
    print(f"DESIGN.md §2: {len(doc_names)} unique token names")

    if orphan_in_css:
        print("\nORPHAN in tokens.css (not documented):")
        for n in orphan_in_css:
            print(" -", n)
    if doc_only:
        print("\nDOC-ONLY in DESIGN.md (not defined in tokens.css):")
        for n in doc_only:
            print(" -", n)

    if orphan_in_css or doc_only:
        return 1
    print("\nMATCH — DESIGN.md §2 documents exactly the tokens.css custom properties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
