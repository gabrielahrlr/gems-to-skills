---
name: gem-to-skill
description: Convert Google Gemini Gems (exported via Google Takeout) into portable Agent Skills. Use whenever the user wants to migrate, port, or convert their Gemini Gems to skills, has a Takeout export with a gemini_gems_data.html file, or asks to turn a Gem's instructions and knowledge files into a SKILL.md. Works with any model, not just Claude.
---

# Gem → Skill migration

This is a **meta-skill**: it produces other skills. It converts Gemini Gems exported from
Google Takeout into the portable Agent Skills format, one gem at a time, with the user
confirming the routing-critical name and description for each.

A Gem and a Skill look similar but differ in one crucial way: a Gem's `Instructions` are a
*persona* and the user picks the gem manually, whereas a Skill's `description` is a
*trigger* that the model uses to auto-select the skill. The main work here is synthesizing
good trigger descriptions — see `references/conversion-guide.md`.

## What the Takeout export contains (and its limits)

The export is a single flat file, `gemini_gems_data.html`, with one block per gem holding
only **Name**, **Instructions**, and a list of **Files** links. That's all. Before doing
anything, internalize these structural limitations and disclose the relevant ones to the
user:

1. **Tools are not exported.** There is no record of which tools a gem used (search, code,
   image generation, connectors). These cannot be inferred and must be confirmed with the
   user where the instructions imply a capability.
2. **Knowledge files: v1 supports two cases** — gems with **no data** (instructions only)
   and gems whose knowledge is in **Google Drive**. For Drive files, the agent reads the
   document directly (asking the user to grant Drive access if needed) and then decides
   where to place the content. Any other link host is out of scope for v1 and is flagged
   for the user. See `references/tier-handling.md`.
3. **Gems have no description** — only persona instructions. You must synthesize the
   skill's `description`, which is what makes it trigger correctly.
4. **The export is all-or-nothing** — it contains every gem; the user selects which to
   convert here.

## Workflow

> **Output goes to the user's Google Drive — always.** This skill runs in environments
> like the Gemini Enterprise App that have no durable local filesystem, so a local-only
> folder would be lost. The finished skill MUST be written into a folder in the user's
> Google Drive and the **Drive link returned to the user** (step 7). The local
> `converted-skills/<name>/` folder is only a temporary staging area for building files
> before upload — never treat it as the final deliverable, and never silently default to
> writing only a local directory. Assume the agent already has the user's Google Drive
> access (OAuth is done in Gemini Enterprise), so no credentials prompt is needed.

### 1. Confirm the Drive destination
Decide where in the user's Google Drive the finished skill(s) should go. Default to
creating a folder named `Converted Skills` (or reuse it if it exists); ask the user only if
they want a different folder. Keep this destination for step 7.

### 2. Locate the export
Ask the user for the path to their Takeout export, or scan for `gemini_gems_data.html`.
The sibling `gemini_scheduled_actions_data.html` is unrelated and can be ignored.

### 3. Parse it
Run the deterministic parser (stdlib-only Python, no dependencies):

```bash
python3 scripts/parse_gems.py <path-to-export-or-dir> -o gems.json
# or, for a quick human-readable view:
python3 scripts/parse_gems.py <path> --pretty
```

This emits each gem with its files and a **tier** computed from the file hosts:
`no_data` (no files), `gdrive` (Google Drive knowledge — includes the extracted
`drive_id`), or `other` (any other host, out of scope for v1).

### 4. Let the user select (point a)
Show the gem list with tier badges and file counts. Ask **which gems** to convert. Don't
assume "all".

### 5. Disclose limitations for the selection (point b)
Based on the tiers of the selected gems, tell the user what to expect:
- `no_data` → clean, fully automatic conversion.
- `gdrive` → the agent reads the Drive file(s) automatically via its native Drive access
  (no upload needed); it only asks the user to grant access if a read is actually denied.
- `other` → not supported automatically in v1; the user can skip it or place the file
  manually.
Always mention the tools-not-exported limitation for any gem whose instructions imply a tool.

### 6. Convert each selected gem
For each gem, in order:

a. **Confirm name + description (point d).** Default the name to the gem's name in
   kebab-case. Synthesize a trigger-oriented description from the instructions using
   `references/conversion-guide.md`. **Show both to the user and let them edit before
   writing** — the description is the routing key, so this step is mandatory.

b. **Read knowledge and decide placement (point c)** following
   `references/tier-handling.md`. For `gdrive` files, **fetch and read the document
   automatically** using its `drive_id` via the agent's native Drive access — do not ask
   the user to upload or download it. Only ask the user to grant access if a read actually
   fails with a permission error. Then decide where the content belongs (inline in the
   body, `references/`, or `assets/`) using the "Deciding where knowledge goes" section of
   `conversion-guide.md`.

c. **Transform** the persona instructions into an operational skill body (role line +
   imperative instructions + pointers to bundled knowledge), per `conversion-guide.md`.

d. **Stage the skill folder** using `assets/skill-template/SKILL.md.tmpl`, into the
   temporary staging area `converted-skills/<skill-name>/`. Place content where you decided
   in step (b). Validate against `references/skill-format.md`. This local folder is staging
   only — the deliverable is the Google Drive upload in step 7.

### 7. Upload to Google Drive and return the link (required)
This step is mandatory — it is how the skill is actually delivered. Using the agent's native
Google Drive access (OAuth is already done in Gemini Enterprise — no credentials prompt):

1. Create (or reuse) the destination folder from step 1, then create a subfolder named
   `<skill-name>` inside it.
2. Upload every file from `converted-skills/<skill-name>/` into that subfolder, preserving
   the structure (`SKILL.md` plus any `references/` and `assets/` files).
3. **Return the shareable Google Drive link** to the `<skill-name>` folder to the user.

Optionally, also upload a single zipped bundle named `<skill-name>.skill` if the user wants
one downloadable artifact. Do not consider the skill delivered until the Drive upload
succeeds and you have given the user the link.

### 8. Summarize and offer handoff
Report per gem: converted cleanly, or needs follow-up (un-read Drive knowledge, `other`-tier
files, unconfirmed tools), plus the **Google Drive link** for each uploaded skill. If the
`skill-creator` skill is available in the environment, offer to hand off the new skills to
it for evaluation and iteration — but this skill is fully standalone and does not require it.

## Reference files

- `references/conversion-guide.md` — persona-instructions → trigger-description mapping,
  naming rules, body transformation, worked example. **Read this before writing any skill.**
- `references/tier-handling.md` — how to fetch/defer each knowledge-file tier.
- `references/skill-format.md` — the portable skill folder format + validity check.
- `assets/skill-template/SKILL.md.tmpl` — template for generated skills.
- `scripts/parse_gems.py` — the deterministic Takeout parser.
