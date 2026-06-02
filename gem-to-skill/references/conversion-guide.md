# Converting a Gem into a Skill

This is the core intellectual work of the meta-skill: a Gem and a Skill look similar but
are routed differently. Getting the `name` + `description` right is what makes the skill
actually fire at the right time.

## The fundamental difference

| | Gemini Gem | Agent Skill |
|---|---|---|
| Identity field | `Instructions` — a **persona** ("You are an expert X…") | `description` — a **trigger** ("Use when the user wants…") |
| How it's selected | User manually picks the gem | Model auto-selects based on `description` |
| Knowledge | Uploaded files attached to the gem | Files bundled under `references/` / `assets/` |

A gem's instructions describe *who the assistant is*. A skill's description must describe
*when to use it and what it does* — because the model reads the description to decide
whether to load the skill at all. **A faithful copy of the gem instructions into the skill
body is correct, but it is not a description.** You must synthesize the description.

## Producing the `description` (the routing key)

Write 1–3 sentences that cover two things:

1. **What it does** — the capability, in plain terms.
2. **When to trigger** — concrete situations, phrasings, or artifacts that should invoke it.

Lean slightly "pushy" on the triggers — models tend to *under*-trigger skills. Name the
real-world situations a user would be in, not just abstract capability.

**Worked example** — gem `hr-onboarding-local`:

> Instructions: *"you are the head of HR at a company and support teams answering questions
> for the onboarding process based on the knowledge shared below."*

Becomes:

> **name:** `hr-onboarding-local`
> **description:** *"Answer employee onboarding questions using the company's HR onboarding
> document. Use whenever someone asks about onboarding steps, first-day setup, required
> paperwork, HR policies, or new-hire processes — even if they don't mention 'HR'."*

Notice what changed: persona ("you are the head of HR") → capability + explicit trigger
situations, and the attached PDF is referenced as the source of truth.

## Producing the `name`

- Default to the **gem's own name**, normalized to kebab-case (lowercase, hyphens, no
  spaces or special characters). E.g. `Create Images For Ads` → `create-images-for-ads`.
- Fix obvious typos only if the user agrees (e.g. `create-images-loca-files`).
- Keep it short and descriptive; the name is secondary to the description for routing but
  should still read sensibly.

## Producing the skill body

Transform the persona-instructions into operational guidance:

1. **Lift the persona into a single role line** at the top of the body
   (e.g. "You act as the company's HR onboarding assistant.").
2. **Convert the rest into imperative instructions** describing how to do the task.
3. **Wire in knowledge** — if files were fetched, point to them explicitly
   ("Base answers on `references/employee-onboarding-process.pdf`; if the answer isn't in
   it, say so.").
4. **Explain the why** where it helps the model generalize, rather than rigid MUST/NEVER
   rules.

## Deciding where knowledge goes

When a gem has Google Drive knowledge and you've read its content (see
`tier-handling.md`), decide where to put it. Skills use **progressive disclosure** — three
loading levels, cheapest first — so place content at the level that matches how often it's
needed:

1. **`SKILL.md` body (always loaded when the skill triggers).** Put small, always-relevant
   knowledge here: a short policy, a handful of key facts, a compact rubric. Keep the body
   focused — if it starts ballooning, push detail down a level.
2. **`references/` (loaded only when needed).** Put larger documents here — a multi-page
   PDF, a long handbook — and point to them from the body
   ("Base answers on `references/<file>`; if it's not covered there, say so."). This keeps
   the skill cheap to load while still grounding it.
3. **`assets/` (used in output, not read as prose).** Put style-reference images and
   templates here. For images, also embed a short textual style description in the body so
   the skill still works on models that can't view images at generation time.

Rules of thumb:
- A few sentences of facts → inline in the body.
- More than roughly a page, or content only some queries need → `references/` with a pointer.
- Binary/visual assets → `assets/`.
- Don't paste a whole PDF into the body; that defeats progressive disclosure and makes the
  skill expensive to load every time.

Every file you reference in the body must actually exist in the skill folder (or be flagged
as a `TODO` if it couldn't be obtained).

## Always confirm with the user before writing

Show the proposed **name** and **description** for each gem and let the user edit them. The
description is the single most important field for whether the skill works in practice, so
this confirmation is not optional.
