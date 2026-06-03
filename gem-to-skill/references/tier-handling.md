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

Each Drive file in `gems.json` has two things you can search on: a `drive_id` (extracted
from the exported link) and a `filename` (the display name, e.g. "Employee Onboarding
Process.pdf"). Use both — the link is frequently stale, but the file usually still lives in
the user's Drive under its name.

### Step 1: find and read the file yourself — this is the default
**Do not ask the user to download, upload, or attach the file.** You have the user's Drive
connected; locate and read the document with your Drive tools. Try, in order, until one
works:

1. **Open by ID** — read the file directly by its `drive_id`.
2. **Search by filename** — search the user's Drive for a file matching `filename` and read
   the best match. Do this whenever the ID lookup fails or returns nothing; in practice the
   same-named document is almost always present in the user's Drive.
3. **Browser automation** (only if available) — open
   `https://drive.google.com/file/d/<drive_id>/view` and read/export it.

### Step 2: only if every method genuinely fails
If the ID lookup, the filename search, and any browser path all fail (e.g. the file is owned
by someone else and not shared, or truly doesn't exist), only then tell the user, note the
file as a `TODO` in the skill body, and move on. Do not block the whole conversion, and do
not fall back to "please put the file under references/".

### Step 3: extract the content and convert it to Markdown
Pull the text out of the document and write it as a clean **Markdown** file at
`references/<filename>.md` (drop the original extension, e.g.
`employee-onboarding-process.pdf` → `references/employee-onboarding-process.md`). This is a
core "good skill" principle: a skill's knowledge should be readable text the model can load,
not a raw binary. Preserve structure (headings, lists, tables) as Markdown. For images, view
them and capture a textual style description instead of text.

### Step 4: decide where to place it
This is a real decision, guided by the Agent Skills progressive-disclosure model — see the
"Deciding where knowledge goes" section in `conversion-guide.md`. In short:

- **Small / always-needed** (a short policy, a few facts) → fold directly into `SKILL.md`.
- **Larger reference material** (a multi-page doc) → keep the `references/<filename>.md` file
  and point to it from `SKILL.md`, so it's loaded only when needed.
- **Images used as style references** → save under `assets/`, and also embed a textual
  style description in the body so the skill degrades gracefully on models that can't see
  images at generation time.

## Always-true limitation: tools are not exported

The Takeout export records **nothing** about which tools a gem used (search, code, image
generation, connectors). This can't be inferred. For any gem whose instructions imply a
tool ("generate images", "search the web"), tell the user the skill will rely on whatever
tools the host model has, and confirm the intended capability.
