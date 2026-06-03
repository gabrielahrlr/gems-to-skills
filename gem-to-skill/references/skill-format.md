# Portable Agent Skill format

This is the minimal, self-contained spec for the skill folders this meta-skill produces, so
it never depends on another skill being installed. The format is the open Agent Skills
format and works with any model/runtime that supports skills.

## Folder layout

```
<skill-name>/
├── SKILL.md          (required)
├── references/       (optional — knowledge as Markdown, loaded as needed)
├── scripts/          (optional — executable helpers)
└── assets/           (optional — files used in output, e.g. style-reference images)
```

The folder name must equal the `name` in the frontmatter.

## SKILL.md

```markdown
---
name: <kebab-case-name>
description: <what it does + when to trigger; this is the routing key>
---

# <Human Title>

<One role line lifted from the gem persona.>

## Instructions

<Imperative, operational instructions transformed from the gem.>

## Knowledge

<Pointers to bundled files, e.g. "Base answers on references/<file>.">
```

### Rules

- **`name`** and **`description`** are the only required frontmatter fields. Keep them
  model-agnostic — no Claude-specific syntax.
- **`description`** is what determines triggering. See `conversion-guide.md`.
- Keep `SKILL.md` focused; push large knowledge into `references/` and point to it, rather
  than pasting it inline (progressive disclosure keeps the skill cheap to load).
- Use relative paths (`references/...`, `assets/...`) so the skill is portable.

## Validity check

A generated skill is valid when:
1. The folder name matches the frontmatter `name`.
2. The frontmatter is parseable YAML with non-empty `name` and `description`.
3. Every file referenced in the body actually exists in the folder (or is flagged as a
   `TODO` if it couldn't be fetched).
