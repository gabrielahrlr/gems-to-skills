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

### Step 1: read the file automatically — this is the default
Fetch and read the Drive file yourself using the `drive_id`. **Do not ask the user to
download or upload the file** — in environments like the Gemini Enterprise App the agent
has native Google Drive access, so reading the document is expected to just work. Try, in
order:

1. **Native Drive access / connector / MCP tool** — read the file directly by its
   `drive_id`. In Gemini Enterprise this is the normal path and needs no user action.
2. **Browser automation** — if a browser tool is available and the user is signed into
   Google, open `https://drive.google.com/file/d/<drive_id>/view` and read/export it.

### Step 2: only if access is genuinely denied
Ask the user to grant access **only** if a read actually fails with a permission/auth error
(e.g. the file is owned by someone else or Drive isn't connected). Don't pre-emptively ask
for uploads — attempt the automatic read first. If access truly can't be obtained, note the
file as a `TODO` in the skill and move on rather than blocking.

### Step 3: extract the content you need
Pull the actual content out of the file (text for docs/PDFs; for images, view them and
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
