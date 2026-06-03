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
   and gems whose knowledge is in **Google Drive**. For Drive files, you find the document
   in the user's Drive yourself (by ID or by filename), extract its text into a Markdown
   reference, and decide where to place it — you never ask the user to upload it. Any other
   link host is out of scope for v1 and is flagged for the user. See
   `references/tier-handling.md`.
3. **Gems have no description** — only persona instructions. You must synthesize the
   skill's `description`, which is what makes it trigger correctly.
4. **The export is all-or-nothing** — it contains every gem; the user selects which to
   convert here.

## Operating environment: use your Google Drive tools

You are running in the Gemini Enterprise App with the user's Google Drive already
connected (OAuth is done). **Google Drive is both your input source and your output
destination, and you must use your Drive tools to do the work yourself.** Two hard rules
that you must not violate, because breaking them is the most common failure of this skill:

- **Never ask the user to upload, download, attach, or "place a file under references/".**
  The source documents are already in the user's Drive — find and read them yourself. The
  output skill must be created in the user's Drive by you, not handed back as instructions.
- **Do the Drive reads and writes with your own Drive tools.** Searching Drive by filename,
  opening a file by its ID, extracting its text, creating folders, and uploading files are
  all things you can do directly. If a specific read fails, try the alternative methods in
  `references/tier-handling.md` before ever involving the user.

If you find yourself about to write a message that asks the user to provide a file or to
move the output somewhere themselves, stop — that means you skipped a Drive tool you should
have used.

## Workflow

> **Output goes to the user's Google Drive — always.** This skill runs in environments
> like the Gemini Enterprise App that have no durable local filesystem, so a local-only
> folder would be lost. The finished skill MUST be written into a folder in the user's
> Google Drive and the **Drive link returned to the user** (step 7). The local
> `converted-skills/<name>/` folder is only a temporary staging area for building files
> before upload — never treat it as the final deliverable, and never silently default to
> writing only a local directory.

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
- `gdrive` → the agent finds the document in the user's Drive (by ID or by filename), reads
  it, and converts it into a Markdown reference — no upload needed; it only involves the
  user if every read method genuinely fails.
- `other` → not supported automatically in v1; the user can skip it or place the file
  manually.
Always mention the tools-not-exported limitation for any gem whose instructions imply a tool.

### 6. Convert each selected gem
For each gem, in order:

a. **Confirm name + description (point d).** Default the name to the gem's name in
   kebab-case. Synthesize a trigger-oriented description from the instructions using
   `references/conversion-guide.md`. **Show both to the user and let them edit before
   writing** — the description is the routing key, so this step is mandatory.

b. **Read knowledge and convert it (point c)** following `references/tier-handling.md`.
   For each `gdrive` file, locate the document in the user's Drive **yourself** — try
   opening it by its `drive_id`, and **also search the user's Drive by the file's name**
   (the exported link is often stale, but a file with the same name usually still exists in
   their Drive). Read the document, **extract its text, and write it as a clean Markdown
   reference file** at `converted-skills/<skill-name>/references/<filename>.md` — do not
   dump a raw PDF and do not ask the user to add the file. Then decide placement (inline,
   `references/`, or `assets/`) using "Deciding where knowledge goes" in
   `conversion-guide.md`. Only involve the user if every read method genuinely fails.

c. **Transform** the persona instructions into an operational skill body (role line +
   imperative instructions + pointers to bundled knowledge), per `conversion-guide.md`.

d. **Stage the skill folder** using `assets/skill-template/SKILL.md.tmpl`, into the
   temporary staging area `converted-skills/<skill-name>/`. Place content where you decided
   in step (b). Validate against `references/skill-format.md`. This local folder is staging
   only — the deliverable is the Google Drive upload in step 7.

### 7. Create the skill in Google Drive and return the link (required)
This step is mandatory — it is how the skill is actually delivered, and you do it yourself
with your Drive tools. Do **not** end the task by describing the files or telling the user
to upload them. Concretely:

1. Using your Drive tools, create (or reuse) the destination folder from step 1, then
   create a subfolder named `<skill-name>` inside it.
2. Create every file from `converted-skills/<skill-name>/` as a real file in that Drive
   subfolder, preserving structure: `SKILL.md`, plus the `references/<filename>.md` files
   and any `assets/` files. The `SKILL.md` and reference files are text — write their
   contents directly into Drive.
3. Verify the files exist in Drive, then **return the shareable Google Drive link** to the
   `<skill-name>` folder.

The task is not done until the files exist in the user's Drive and you have given them the
link. If a Drive write fails, retry with your tools — do not hand the work back to the user.

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
