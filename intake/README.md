# The intake room's tool service

The two tools behind the portal's explainer agent ([docs/staff-portal.md](../docs/staff-portal.md), "The intake room"), and the draft store the review page is built on ([docs/staff-portal-screens.md](../docs/staff-portal-screens.md), section 1).  It holds a person's draft and reads research compliance's files, and nothing else.

**Nothing here runs on the classroom.**  No recipe in the justfile loads `compose.yml` in this directory.  A portal box layers it from its own `site/` under the `intake` profile.

## The tools

| Tool | Writes | What it does |
|---|---|---|
| `draft_fields` | yes | Drafts the fields of a submission from what the person said, in their words, and returns the link to the review page.  An empty call (or one whose values are all empty) lists the fields and writes nothing, so exploring makes no record.  It lists a person-only field's choices in the page's order and never writes one.  It never redrafts a field the person has changed or confirmed on the page.  Its answer names what it saved, and the agent says only that. |
| `timeline` | no | The dated table of obligations.  It says what today is first, writes every date out in words with the month named, keeps each row's schedule apart from its status at the last check, and says how old that check is.  A row whose date passed after the check while it still says pending is marked as the table being behind. |

Identity is the platform's track (@xram, 11-11): the chat presents `INTAKE_MCP_TOKEN` and stamps `X-User-Email`, as with `usage-mcp`.  Only this platform's chat calls it.

## The draft

Per field: the agent's draft, the value, when the person confirmed it (this server's clock), and whether the value differs from the draft, whitespace aside.  That is counsel's whole list.  `drafts.submission` assembles what the office receives from those alone: the value or "not answered", the confirmation time and the changed mark.  It never includes the draft text or anything from the conversation.

The page's operations are in `svc/drafts.py` (`person_set`, `confirm`, `put_draft_back`, `delete`, `submit`).  The page itself is not built yet.  It signs people in itself against the portal's issuer (Esmerelda, 11-11), so no edge header is involved, and it opens a draft only for its owner.  A missing, expired, deleted or someone else's draft gives one answer.

An unsent draft is deleted on its own after `INTAKE_DRAFT_DAYS`.  The number is the office's, so it has no default and the service won't start without it.  A sent draft stays as the office's record.  Where it goes from here (mail, a queue, the office's system) is not decided.

## Files it reads, kept outside this repository

`INTAKE_FIELDS` is research compliance's field list (`intake-fields.yaml`), and `INTAKE_OBLIGATIONS` its dated table (`dated-obligations.yaml`).  Both follow the rules and change when they do, so they live beside the office's notes, and the box mounts them read-only (`INTAKE_KB`).  A field whose choices are still to be copied from the primary text (`options_from`) is listed as not loaded, never guessed.

## Tests

```
python -m pytest -q tests        # 11 pass; the last checks the office's own files when they are on the machine
```
