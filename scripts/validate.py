#!/usr/bin/env python3
"""Deterministic structural checks for the Argus plugin.

Runs in CI and locally. Does NOT run the LLM review. It only verifies that the
plugin manifests, the skill contract, and the lens/knowledge maps are internally
consistent, so a rename or version drift fails fast.

Usage: python3 scripts/validate.py
Exit code 0 = all checks passed, 1 = one or more failed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "review"
LENSES_DIR = SKILL_DIR / "lenses"
REFS_DIR = SKILL_DIR / "references"

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_json_manifests() -> None:
    plugin_path = ROOT / ".claude-plugin" / "plugin.json"
    market_path = ROOT / ".claude-plugin" / "marketplace.json"

    try:
        plugin = json.loads(read(plugin_path))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"{plugin_path.name}: not valid JSON ({e})")
        plugin = {}
    else:
        for key in ("name", "description", "version"):
            if not plugin.get(key):
                fail(f"plugin.json: missing required key '{key}'")
        if "your-github-username" in json.dumps(plugin):
            fail("plugin.json: placeholder 'your-github-username' not replaced")

    try:
        market = json.loads(read(market_path))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"{market_path.name}: not valid JSON ({e})")
        market = {}
    else:
        if not market.get("name"):
            fail("marketplace.json: missing required key 'name'")
        plugins = market.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            fail("marketplace.json: 'plugins' must be a non-empty list")
        else:
            for i, p in enumerate(plugins):
                if not p.get("name") or not p.get("source"):
                    fail(f"marketplace.json: plugins[{i}] needs 'name' and 'source'")

    return plugin


def check_version_matches_changelog(plugin: dict) -> None:
    version = plugin.get("version")
    if not version:
        return
    changelog = read(ROOT / "CHANGELOG.md")
    m = re.search(r"^##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog, re.MULTILINE)
    if not m:
        fail("CHANGELOG.md: no released version heading like '## [1.0.0]' found")
    elif m.group(1) != version:
        fail(
            f"version mismatch: plugin.json is {version} but the latest "
            f"CHANGELOG.md heading is {m.group(1)}"
        )


def check_skill_frontmatter() -> None:
    skill = read(SKILL_DIR / "SKILL.md")
    fm = re.match(r"^---\n(.*?)\n---", skill, re.DOTALL)
    if not fm:
        fail("SKILL.md: missing YAML frontmatter block")
        return
    block = fm.group(1)
    for key in ("name", "description"):
        if not re.search(rf"^{key}\s*:", block, re.MULTILINE):
            fail(f"SKILL.md frontmatter: missing '{key}'")


def _parse_dependency_map() -> dict[str, list[str]]:
    """Parse the 'Lens to knowledge-domain dependency map' table in
    references/README.md into {lens: [domains]}."""
    text = read(REFS_DIR / "README.md")
    section = re.search(
        r"dependency map(.*?)(?:\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE
    )
    if not section:
        fail("references/README.md: 'dependency map' section not found")
        return {}
    mapping: dict[str, list[str]] = {}
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        lens, domains = cells
        if lens.lower() in ("lens", "") or set(lens) <= {"-", " "}:
            continue  # header / separator row
        mapping[lens] = [d.strip() for d in domains.split(",") if d.strip()]
    return mapping


def check_lens_and_domain_consistency() -> None:
    mapping = _parse_dependency_map()
    if not mapping:
        return

    lens_files = {p.stem for p in LENSES_DIR.glob("*.md")}
    mapped_lenses = set(mapping.keys())

    for lens in mapped_lenses - lens_files:
        fail(f"dependency map names lens '{lens}' but lenses/{lens}.md is missing")
    for lens in lens_files - mapped_lenses:
        fail(f"lenses/{lens}.md exists but is not in the dependency map")

    digest_files = {
        p.stem for p in REFS_DIR.glob("*.md") if p.stem not in ("README", "bibliography")
    }
    for lens, domains in mapping.items():
        for domain in domains:
            if domain not in digest_files:
                fail(
                    f"dependency map: lens '{lens}' loads domain '{domain}' but "
                    f"references/{domain}.md is missing"
                )


def _defined_citation_keys() -> set[str]:
    """Keys defined in bibliography.md as '**[KEY]**'."""
    text = read(REFS_DIR / "bibliography.md")
    return set(re.findall(r"\*\*\[([A-Z][A-Z0-9-]+)\]\*\*", text))


def check_citation_integrity() -> None:
    """Every bracketed citation key used in a lens or a knowledge digest must be
    defined in bibliography.md. The framework's rule is that no claim ships without a
    keyed source; this makes that rule enforceable instead of aspirational."""
    defined = _defined_citation_keys()
    if not defined:
        fail("bibliography.md: no '**[KEY]**' source definitions found")
        return

    md_files = sorted(LENSES_DIR.glob("*.md")) + [
        p for p in sorted(REFS_DIR.glob("*.md")) if p.name != "bibliography.md"
    ]
    for path in md_files:
        used = set(re.findall(r"\[([A-Z][A-Z0-9-]+)\]", read(path)))
        for key in sorted(used - defined):
            fail(
                f"{path.relative_to(ROOT)}: cites [{key}] but it is not defined in "
                f"bibliography.md"
            )


def check_lens_header_matches_map() -> None:
    """Each lens declares its knowledge domains in a '**Knowledge domains:**' header
    line. That declaration must match the lens's row in the dependency map, so the two
    sources of truth cannot drift (references/README.md promises they stay in sync)."""
    mapping = _parse_dependency_map()
    if not mapping:
        return
    for lens_path in sorted(LENSES_DIR.glob("*.md")):
        lens = lens_path.stem
        if lens not in mapping:
            continue  # missing-from-map is reported by check_lens_and_domain_consistency
        m = re.search(r"\*\*Knowledge domains:\*\*\s*(.+?)\.", read(lens_path))
        if not m:
            fail(f"lenses/{lens}.md: missing a '**Knowledge domains:**' header line")
            continue
        header_domains = {d.strip() for d in m.group(1).split(",") if d.strip()}
        map_domains = set(mapping[lens])
        if header_domains != map_domains:
            fail(
                f"lenses/{lens}.md: header domains {sorted(header_domains)} do not "
                f"match the dependency map {sorted(map_domains)}"
            )


def _parse_dispatch_lens_column() -> str:
    """Return the concatenated text of the 'Lenses to engage' column of the SKILL.md
    dispatch table (section 2). The artifact column is excluded on purpose."""
    text = read(SKILL_DIR / "SKILL.md")
    section = re.search(r"Dispatch map:(.*?)(?:\n##\s|\Z)", text, re.DOTALL)
    if not section:
        fail("SKILL.md: 'Dispatch map:' table not found")
        return ""
    cells: list[str] = []
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        row = [c.strip() for c in line.strip("|").split("|")]
        if len(row) != 2:
            continue
        artifact, lenses = row
        if artifact.lower().startswith("artifact") or set(artifact) <= {"-", " "}:
            continue  # header / separator row
        cells.append(lenses)
    return " ".join(cells)


def check_dispatch_table_lenses() -> None:
    """The SKILL.md dispatch table and the lens files must agree: every lens file is
    dispatched somewhere, and every hyphenated lens token in the table resolves to a
    real lens. (README.md and CONTRIBUTING.md both claim CI enforces this.)"""
    lens_files = {p.stem for p in LENSES_DIR.glob("*.md")}
    if not lens_files:
        fail("lenses/: no lens files found")
        return
    column = _parse_dispatch_lens_column()
    if not column:
        return

    # Every lens file must appear in the dispatch table.
    for lens in sorted(lens_files):
        if not re.search(rf"\b{re.escape(lens)}\b", column):
            fail(f"lenses/{lens}.md exists but is not referenced in the SKILL.md dispatch table")

    # Every multi-word (hyphenated) lens token in the table must be a real lens. Prose
    # in the lens column is plain words; only lens names are hyphenated, so this catches
    # a renamed or typo'd lens without flagging ordinary text.
    for token in sorted(set(re.findall(r"[a-z]+(?:-[a-z]+)+", column))):
        if token not in lens_files:
            fail(f"SKILL.md dispatch table references lens '{token}' but lenses/{token}.md is missing")


def check_golden_projects() -> None:
    """Every validation/golden-project-* must carry its golden file. This is
    engine-agnostic on purpose: a future non-Prisma fixture need not have a
    schema.prisma, but it must declare what a passing review produces."""
    val_dir = ROOT / "validation"
    projects = sorted(p for p in val_dir.glob("golden-project-*") if p.is_dir())
    if not projects:
        fail("validation/: no golden-project-* directories found")
        return
    for proj in projects:
        if not (proj / "expected-findings.md").is_file():
            fail(f"validation/{proj.name}: missing expected-findings.md")


def main() -> int:
    plugin = check_json_manifests()
    check_version_matches_changelog(plugin)
    check_skill_frontmatter()
    check_lens_and_domain_consistency()
    check_citation_integrity()
    check_lens_header_matches_map()
    check_dispatch_table_lenses()
    check_golden_projects()

    if errors:
        print("FAIL: Argus structural validation")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: Argus structural validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
