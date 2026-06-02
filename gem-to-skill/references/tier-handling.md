# Handling knowledge files by tier

`parse_gems.py` classifies every file into one of four tiers from its host + extension.
This file explains how to fetch (or gracefully defer) each one. Always tell the user up
front which tier each selected gem falls into, so the limitations are clear before work
starts.

## `simple` — instructions only

No files. Fully automatic: synthesize name + description, transform instructions, write
the skill. Nothing to fetch.

## `direct_download` — public download link

Host like `contribution.usercontent.google.com`. These are the Takeout export's own blob
links and are downloadable without authentication.

```bash
curl -L -o "converted-skills/<skill>/references/<filename>" "<url>"
```

Then reference the file from the generated SKILL.md. This is the smoothest non-trivial
case. (Note: these links can expire — fetch promptly. If `curl` returns an HTML login page
instead of the file, treat it as a `drive_doc` and fall back to manual download.)

## `drive_doc` — Google Drive document, needs auth

Host like `drive.google.com`. Not publicly downloadable. Resolve **in this order**:

1. **Drive MCP / connector** — if a Google Drive tool is available in the session, use it
   to fetch the file by its Drive ID. Extract the ID from the URL:
   - `drive.google.com/open?id=<ID>`
   - `drive.google.com/file/d/<ID>/view`
2. **Browser automation** — if a browser tool is available and the user is signed in, open
   the link and download.
3. **Guided manual fallback** — if neither exists, give the user explicit steps:
   > "I can't reach this Drive file automatically. Please download it from `<url>` and
   > place it at `converted-skills/<skill>/references/<filename>`, then tell me when done."
   Pause and continue once the file is present (or the user says to skip it).

Never fail silently — always either fetch it or hand the user a concrete manual step.

## `image_knowledge` — image used as a style reference (hardest)

Hosts like `drive.google.com`, `lh3.google.com`, `googleusercontent`. These gems used
uploaded images as *visual style* references (e.g. "generate images in this style").

**Fidelity warning — state this to the user:** a text-based skill cannot fully reproduce a
visual style the way the original gem (with the images in context) could. Set expectations.

Fetch the same way as `drive_doc` (connector → browser → manual). On success:
- Store images under `converted-skills/<skill>/assets/`.
- Reference them in the body as examples ("Match the visual style of the images in
  `assets/`: note their color palette, lighting, and composition.").
- If the target model can't see images at generation time, additionally ask the user (or
  use a vision pass) to capture a **textual style description** and embed that, so the
  skill degrades gracefully.

If the images can't be fetched, write the skill with a clear `TODO` placeholder in the body
and note it in the final summary so the user knows what's missing.

## Always-true limitation: tools are not exported

The Takeout export records **no information about which tools a gem used** (web search,
code execution, image generation, connectors, etc.). You cannot infer this from the export.
For any gem whose instructions imply a tool (e.g. "generate images"), tell the user that
the skill will rely on whatever tools the host model has, and ask them to confirm the
intended capability.
