# Handling knowledge files

v1 supports exactly two cases, which `parse_gems.py` labels per gem:

- **`no_data`** — the gem has no knowledge files.
- **`gdrive`** — the gem's knowledge lives in Google Drive.

A third label, **`other`**, covers any non-Drive link (expired Takeout blobs,
`lh3.google.com` Photos thumbnails, etc.). These are **out of scope for v1** — tell the
user the file can't be handled automatically and let them either skip it or download it
manually into the new skill's folder.

## `no_data` — instructions only

Fully automatic. Synthesize name + description, transform the instructions into the skill
body, write the skill. Nothing to fetch, no placement decision beyond the body itself.

## `gdrive` — read the file from Google Drive

`parse_gems.py` extracts the Drive **file ID** for each Drive file (`drive_id` field). Use
it to read the document, then decide where the content belongs.

### Step 1: read the file
Read the Drive file using whatever Drive access this environment has, in order:

1. **Google Drive connector / MCP tool** — if one is available, read the file by its
   `drive_id`. This is the preferred path.
2. **Browser automation** — if a browser tool is available and the user is signed into
   Google, open `https://drive.google.com/file/d/<drive_id>/view` and read/export it.

### Step 2: if you can't access it, ask for access
If no Drive access is available, or the read fails with a permission error, **ask the user
to grant access** rather than giving up — for example: connect/authenticate their Google
Drive, or open the document so it's reachable. Then retry. Only as a last resort, ask the
user to manually download the file into the skill's folder.

Never fail silently — either read the file, or hand the user a concrete next step.

### Step 3: read the actual content
Once reachable, read the document's contents (text for docs/PDFs; for images, view them and
capture a textual description of their style). You need the content, not just the link,
because the original gem had these files in context and the new skill won't unless you
embed or bundle them.

### Step 4: decide where to place it
This is a real decision, guided by the Agent Skills progressive-disclosure model — see the
"Deciding where knowledge goes" section in `conversion-guide.md`. In short:

- **Small / always-needed** (a short policy, a few facts) → fold directly into `SKILL.md`.
- **Larger reference material** (a multi-page PDF, a long doc) → save under `references/`
  and point to it from `SKILL.md`, so it's loaded only when needed.
- **Images used as style references** → save under `assets/`, and also embed a textual
  style description in the body so the skill degrades gracefully on models that can't see
  images at generation time.

## Always-true limitation: tools are not exported

The Takeout export records **nothing** about which tools a gem used (search, code, image
generation, connectors). This can't be inferred. For any gem whose instructions imply a
tool ("generate images", "search the web"), tell the user the skill will rely on whatever
tools the host model has, and confirm the intended capability.
