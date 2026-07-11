## What this changes

Briefly describe the change and the gap it closes.

## Type

- [ ] New / changed lens
- [ ] Knowledge-base (`references/`) update
- [ ] New / changed golden project
- [ ] Docs / meta / CI
- [ ] Other

## Checklist

- [ ] If a lens was added or renamed, the **dispatch table** in
      `skills/review/SKILL.md` and the **lens → domain map** in
      `skills/review/references/README.md` are in sync.
- [ ] Any new reviewer guidance upholds the **evidence gate** (finding → evidence →
      reasoning → impact → recommendation → trade-offs → confidence) and adds no
      generic filler.
- [ ] Knowledge additions cite canonical sources keyed to `references/bibliography.md`
      (Critical/High findings never rest on the provenance tier alone).
- [ ] If reviewer behavior changed, the affected `validation/**/expected-findings.md`
      is updated.
- [ ] `CHANGELOG.md` updated (and `.claude-plugin/plugin.json` version bumped if
      cutting a release).
- [ ] `python3 scripts/validate.py` passes locally.
