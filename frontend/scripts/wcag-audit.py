#!/usr/bin/env python3
"""WCAG 2.1 AA contrast audit over the v6 token palette — every text/background pair the UI
actually produces, INCLUDING accent/sale text on every tinted surface (the class of failure the
v5 review caught). Run: python3 frontend/scripts/wcag-audit.py — exits 1 on any failure."""

import sys


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def f(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(fg: str, bg: str) -> float:
    hi, lo = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


LIGHT = {
    "surface": "#FFFFFF", "surface2": "#F5F5F4", "band": "#F7E5D2", "canvas": "#F5F5F4",
    "text": "#18181B", "muted": "#54555A", "subtle": "#6E6F75",
    "accent": "#C2410C", "accent_text": "#B33A05", "on_accent": "#FFFFFF",
    "bright": "#FF8A00", "on_bright": "#221100", "sale": "#C62828", "sale_bg": "#FDEBEA",
    "nav_bg": "#1B1B1E", "nav_text": "#D9D8D4", "nav_hi": "#FFFFFF",
    "side_bg": "#FFFFFF", "side_text": "#54555A",
}
DARK = {
    "surface": "#1E1E1F", "surface2": "#28282A", "band": "#2A2118", "canvas": "#111112",
    "text": "#F0EFEC", "muted": "#ABAAA5", "subtle": "#8A8984",
    "accent": "#FF9D45", "accent_text": "#FFA657", "on_accent": "#221100",
    "bright": "#FF8A00", "on_bright": "#221100", "sale": "#FF8A80", "sale_bg": "#33201E",
    "nav_bg": "#111112", "nav_text": "#ABAAA5", "nav_hi": "#FFFFFF",
    "side_bg": "#1A1A1B", "side_text": "#ABAAA5",
}


def audit(name: str, p: dict[str, str]) -> list[str]:
    checks = [
        # (label, fg, bg, floor)  — 4.5 normal text; 3.0 large-only/graphic
        ("text on surface", p["text"], p["surface"], 4.5),
        ("text on surface-2", p["text"], p["surface2"], 4.5),
        ("text on band", p["text"], p["band"], 4.5),
        ("text on canvas", p["text"], p["canvas"], 4.5),
        ("muted on surface", p["muted"], p["surface"], 4.5),
        ("muted on surface-2", p["muted"], p["surface2"], 4.5),
        ("muted on band", p["muted"], p["band"], 4.5),
        ("subtle on surface", p["subtle"], p["surface"], 4.5),
        ("accent-text on surface", p["accent_text"], p["surface"], 4.5),
        ("accent-text on surface-2", p["accent_text"], p["surface2"], 4.5),
        ("accent-text on band", p["accent_text"], p["band"], 4.5),
        ("on-accent on accent (buttons)", p["on_accent"], p["accent"], 4.5),
        ("on-bright on bright (badges)", p["on_bright"], p["bright"], 4.5),
        ("sale on surface", p["sale"], p["surface"], 4.5),
        ("sale on sale-bg", p["sale"], p["sale_bg"], 4.5),
        ("nav text on nav bg", p["nav_text"], p["nav_bg"], 4.5),
        ("nav hi on nav bg", p["nav_hi"], p["nav_bg"], 4.5),
        ("side text on side bg", p["side_text"], p["side_bg"], 4.5),
    ]
    failures: list[str] = []
    for label, fg, bg, floor in checks:
        r = ratio(fg, bg)
        status = "PASS" if r >= floor else "FAIL"
        print(f"  {status}  {r:5.2f}  {label}")
        if r < floor:
            failures.append(f"{name}: {label} = {r:.2f} (< {floor})")
    return failures


def main() -> int:
    all_failures: list[str] = []
    for name, palette in (("LIGHT", LIGHT), ("DARK", DARK)):
        print(f"{name}:")
        all_failures += audit(name, palette)
    if all_failures:
        print("\nFAILURES:")
        for f in all_failures:
            print(" -", f)
        return 1
    print("\nAll pairs pass WCAG 2.1 AA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
