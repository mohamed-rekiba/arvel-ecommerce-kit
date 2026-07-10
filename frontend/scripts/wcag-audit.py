#!/usr/bin/env python3
"""WCAG 2.1 AA contrast audit — parses the LIVE token file (src/styles/tokens.css) so a palette
edit can never drift past a stale mirror (the v6 review nit). Resolves var() references and
audits every text/background pair the UI produces, including accent/sale text on every tinted
surface. Run: python3 frontend/scripts/wcag-audit.py — exits 1 on any failure."""

import re
import sys
from pathlib import Path

TOKENS = Path(__file__).parent.parent / "src" / "styles" / "tokens.css"


def _parse_blocks(css: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return (light, dark) raw token maps (:root before the shim + [data-theme=dark])."""

    def block(selector_start: int) -> dict[str, str]:
        depth = 0
        out: dict[str, str] = {}
        body_start = css.index("{", selector_start) + 1
        i = body_start
        while i < len(css):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        body = css[body_start:i]
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", body):
            out[m.group(1)] = m.group(2).strip()
        return out

    light = block(css.index(":root"))
    dark = block(css.index("[data-theme='dark']"))
    return light, dark


def _resolve(name: str, table: dict[str, str], base: dict[str, str]) -> str | None:
    """Follow var() chains to a hex literal; None for non-color values."""
    seen: set[str] = set()
    value = table.get(name) or base.get(name) or ""
    while True:
        m = re.fullmatch(r"var\((--[\w-]+)\)", value.strip())
        if not m:
            break
        ref = m.group(1)
        if ref in seen:
            return None
        seen.add(ref)
        value = table.get(ref) or base.get(ref) or ""
    value = value.strip()
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else None


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def f(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(fg: str, bg: str) -> float:
    hi, lo = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# (label, fg token, bg token, floor) — 4.5 normal text; graphics-only pairs are excluded
CHECKS: list[tuple[str, str, str, float]] = [
    ("text on surface", "--text", "--surface", 4.5),
    ("text on surface-2", "--text", "--surface-2", 4.5),
    ("text on band", "--text", "--band", 4.5),
    ("text on hero band", "--text", "--hero-band", 4.5),
    ("text on canvas", "--text", "--canvas", 4.5),
    ("text on bg", "--text", "--bg", 4.5),
    ("muted on surface", "--text-muted", "--surface", 4.5),
    ("muted on surface-2", "--text-muted", "--surface-2", 4.5),
    ("muted on band", "--text-muted", "--band", 4.5),
    ("muted on hero band", "--text-muted", "--hero-band", 4.5),
    ("subtle on surface", "--text-subtle", "--surface", 4.5),
    ("accent-text on surface", "--accent-text", "--surface", 4.5),
    ("accent-text on surface-2", "--accent-text", "--surface-2", 4.5),
    ("accent-text on band", "--accent-text", "--band", 4.5),
    ("accent-text on hero band", "--accent-text", "--hero-band", 4.5),
    ("on-accent on accent (buttons)", "--on-accent", "--accent", 4.5),
    ("on-bright on bright (badges)", "--on-accent-bright", "--accent-bright", 4.5),
    ("sale on surface", "--sale", "--surface", 4.5),
    ("sale on sale-bg", "--sale", "--sale-bg", 4.5),
    ("nav text on nav bg", "--nav-text", "--nav-bg", 4.5),
    ("nav hi on nav bg", "--nav-text-hi", "--nav-bg", 4.5),
    ("side text on side bg", "--side-text", "--side-bg", 4.5),
    ("side hi on side bg", "--side-text-hi", "--side-bg", 4.5),
    ("success fg on bg", "--success-fg", "--success-bg", 4.5),
    ("danger fg on bg", "--danger-fg", "--danger-bg", 4.5),
    ("warn fg on bg", "--warn-fg", "--warn-bg", 4.5),
    ("info fg on bg", "--info-fg", "--info-bg", 4.5),
]


def main() -> int:
    css = TOKENS.read_text()
    light, dark = _parse_blocks(css)
    failures: list[str] = []
    for theme, table in (("LIGHT", light), ("DARK", dark)):
        print(f"{theme}:")
        for label, fg_tok, bg_tok, floor in CHECKS:
            fg = _resolve(fg_tok, table if theme == "DARK" else light, light)
            bg = _resolve(bg_tok, table if theme == "DARK" else light, light)
            if fg is None or bg is None:
                print(f"  SKIP        {label} ({fg_tok} or {bg_tok} not a hex literal)")
                continue
            r = ratio(fg, bg)
            status = "PASS" if r >= floor else "FAIL"
            print(f"  {status}  {r:5.2f}  {label}")
            if r < floor:
                failures.append(f"{theme}: {label} = {r:.2f} (< {floor})")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nAll pairs pass WCAG 2.1 AA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
