---
title: Which guide has it?
description: A proposed tool that tells a guide how many strong matches each guide's documentation has for a question, so a hand-off goes to the guide whose files hold the answer and not to the one whose one-line description sounds closest.
audience: operator
also_reaches: [builder]
status: proposed
owner: piper
tags: [tool-calling, token-economy, rendered-config, least-privilege, librechat]
tethered_to:
  - docs/agent-contract.md
  - docs/corpus.py
  - scripts/seed_agents.py
  - compose.yml
  - librechat/librechat.yaml
---

# Which guide has it?

**Status: proposed, 2026-10-02.**  Pedagogy's spec; the service is registrar-family code, so @marco is author-of-record for the build and @geordi for the deploy.  Nothing here exists yet.

Asked about rate limits on 2026-10-02, the Instructor Guide said "Rate limits are covered by the Usage Guide" and sent the person there.  It had no way to know.  It had searched its own files, found nothing, and picked the sibling whose line in the guide directory sounded closest — "what the numbers mean — tokens, context, cost."

The Usage Guide had no page that mentioned rate limits.  The only answer anywhere was one line in the registrar spec — "per-message rate limits (budgets are the governor)" — and that page sits on the Operator, Platform and Security shelves.  Those same shelves also say "rate limit" a dozen times about TLS certificates and LibreChat's upload limit.  So the guess went to a guide with nothing, and a word count would have sent a professor to a page about ACME.

The gap is closed now.  [When it breaks](../apex/building-with-code/when-it-breaks.md) and [Reading your own numbers](../apex/understanding-your-usage/reading-your-numbers.md) both say there are no per-message rate limits, and the Instructor Guide carries both pages, so it answers that question itself.  The pattern behind it hasn't changed: a guide that comes up empty still picks a sibling by its description.

Every hand-off works that way today.  Each guide carries its own pages and the shared rules, and it knows the other six guides only by a one-line description ([the guide-agent contract](agent-contract.md), "WHERE TO SEND PEOPLE").  The hand-off itself has a shape now — name the guide, switch to it at the top and press enter, it sees this conversation — but the choice of guide is a guess from a description.

This spec gives the guide one piece of evidence: for a question, how many pages in each guide's documentation match it strongly.  Counts only.  The guide needs enough to choose with confidence, and page text from six other shelves would flood its context with material it cannot cite.

## What the tool returns

One tool, `which_guide(question)`.  The guide passes the question in its own words, and it gets back:

```text
Pages that match this question strongly, by guide:
  Coder Guide        4
  Operator Guide     1
No strong matches in the other guides.
```

- **Pages, not chunks.**  A page counts once if any of its chunks clears the threshold.  A long page split into nine chunks would otherwise outvote three short pages that each answer the question.
- **Every guide with a corpus is listed, the caller included.**  The tool does not know which agent called it, and it doesn't need to: the prompt tells the guide its own name is in the list too.
- **The Front Desk is never listed.**  It has no pages.
- **Zero everywhere is an answer**, and it says so: "No guide's documentation matches this strongly."  That is the evidence for "I don't know."
- **No titles, no excerpts, no scores.**  A title invites the guide to describe a page it hasn't read, which is [the fabrication](agent-contract.md#the-fabrication-observed-2026-09-11) by another route.  A score invites arithmetic.

## How a guide uses it

Added to the preamble's WHEN YOUR FILES DON'T SAY, in place of choosing from the directory alone:

```text
If your own search finds nothing, call which_guide with the question in
your own words.  It tells you how many pages in each guide's documentation
match it strongly; your own name is in the list too.

  * If another guide has the most, hand the question to that guide.
  * If two guides tie, name both and say which to open first.
  * If your own count is highest, the answer is in your files: search
    them again with the words the tool's best match would use, and answer.
  * If every count is zero, say "That isn't in the documentation I have,"
    and name the nearest thing your files do cover.

Never quote the counts to the person.  They are for choosing, and a
number they didn't ask for reads as machinery.
```

The Front Desk gets the same tool and a shorter rule: on a platform question, call `which_guide` and send the person to the guide with the most matches; on a tie, name both.  Today the desk routes on the directory alone, and it is the agent most exposed to a confident wrong guess (agent-contract.md, "The front desk").

## Where the counts come from

**The counts have to agree with what the next guide's own search will find.**  A count of four that the receiving guide's `file_search` can't reproduce sends the person to a guide that then says it doesn't know.  So the index uses the same embedding model, the same chunking and the same text as the guides' knowledge files.

**It keeps its own index rather than querying `rag_api`.**  The vestibule's `rag_api` (`alm-rag`) already holds every guide's pages, embedded, and `site/agents-state.json` maps each guide to its file ids.  Querying it would give exactly matching scores.  But `rag_api` authenticates with an HS256 token signed by `JWT_SECRET`, and on the flagship that is the secret LibreChat signs every user session with ([design walls](design-walls.md), "Course instances cannot talk to `rag_api`").  A service holding it can mint a session for anyone in the vestibule, operators included.  A routing aid is not worth a credential that can impersonate an admin.

So the service builds its own copy:

- **Image:** `FROM` the pinned `RAG_API_IMAGE`, plus `fastmcp`.  That image already has the splitter and the Hugging Face embeddings `rag_api` uses, so chunking and embedding run the same code.  Verify both against the pinned image's `app/` before trusting it: the splitter settings (`CHUNK_SIZE` / `CHUNK_OVERLAP`, defaults 1500 / 100 as far as we know) and whether queries are embedded with an instruction prefix.
- **Model:** `EMBEDDINGS_MODEL` from compose (`BAAI/bge-small-en-v1.5` today), with the `hf-cache` volume mounted read-only, so no second download and no egress at run time.
- **Text:** `corpus/<guide>/*.md`, the files `seed_agents.py` uploads, minus `MANIFEST.md`, `SYSTEM-PROMPT.md` and `EVALS.md` (its `NOT_KNOWLEDGE`).  Mounted read-only, as a directory ([design walls](design-walls.md): never a single file that gets rewritten).
- **Index:** in memory.  Every unique page is embedded once, keyed by content hash, since the shelves share many pages.  About a hundred pages comes to a few hundred chunks, which is seconds on CPU.  The index rebuilds when the corpus directory's hashes change, checked on each call.  `docs-corpus` runs before `agents-refresh` in `deploy`, so the index and the guides' knowledge move together.
- **Holds no credentials.**  No database, no `JWT_SECRET`, no LiteLLM key.  It reads public documentation and answers with integers.

**Lexical search was considered and set aside.**  A BM25 index built by `docs/corpus.py` at render time would need no new service.  But its notion of a match isn't the guides' — a question phrased in a student's words would score zero where `file_search` finds the page, which is the mismatch the counts exist to avoid.

## Wiring

- **Service:** `guide-index` in `compose.yml`, on the internal network, no published port.  It belongs to the vestibule, not to courses: the course fleet's chats carry no tools (decision 31), and nothing in a course needs it.
- **MCP server key:** `<MCP_SERVER_PREFIX>-guides`, declared under `mcpServers:` in `librechat/librechat.yaml` next to `-courses` and `-usage`.  `mcpSettings.allowedDomains` lists the platform's own hosts first ([design walls](design-walls.md), "MCP servers staff add"), so `guide-index` goes on that list or the vestibule refuses it.
- **Seeder:** a `GUIDES_MCP` key and a `_G()` name builder in `scripts/seed_agents.py`, added to `MCP_SERVERS` before any guide uses it — `_check_guides()` refuses a tool on an undeclared server, by design.  `which_guide` goes on every guide and on the Front Desk.
- **Identity:** none needed.  The tool answers the same for everyone, and it reads no trusted headers.
- **Logging:** the counts and the time, never the question.  Questions are what people typed, and this service has no reason to keep them.

## Cost

- **Tokens:** one tool schema on seven agents.  A two-line description and one string argument come to roughly a hundred tokens a turn, against the ~4,200 the course chat's tools cost before decision 31.  Write the description short and measure the schema on the box.
- **Calls:** one per hand-off, only after the guide's own search came up empty.  In-scope questions never reach it.
- **CPU:** one query embedding per call, milliseconds with bge-small.

## The threshold

"Strong" is a cosine-similarity cutoff, and it has to be measured.  Guessing it is how a count of four turns into a page that mentions the word once.

1. **Collect labeled questions.**  Take every eval case whose owning guide is known — F, R, H and the tool cases — plus the routing cases below.  Add the questions that reach `report_problem` with "wrong guide" once there are any.
2. **Score candidate cutoffs.**  For each one, ask whether the guide with the most pages is the owning guide.  Choose the cutoff that routes the most questions correctly while sending the fewest off-topic questions anywhere at all (P1–P4 should come back zero everywhere).
3. **Write it down.**  Record the cutoff, the model and the date in [design walls](design-walls.md) as the measured value.  An embedding model change invalidates it, and `render-check`-style drift should say so — the cutoff is pinned to the model it was measured on.

**Shelf size is the bias to watch.**  The Student Guide has 29 pages and the Usage Guide six, so a loose cutoff favors the big shelves.  If calibration shows that, report each count as a share of the guide's pages, and keep the guide-facing output as integers either way.

## The evals

Tool cases in the contract's `expect:` format, so `just evals-check` scores the calls.  Whether the right guide was named is still a person's read of the transcript.

```yaml
- id: H2
  pattern: route on evidence
  guides: [usage-guide]
  as: instructor
  turns:
    - "What should my syllabus say about students using AI?"
  expect:
    - calls: [which_guide]
  passes_when: >
    Names the guide which_guide ranked first and says to switch and press
    enter.  Fails if it names a guide from the directory without calling
    the tool, or quotes the counts to the person.  On today's corpus the
    syllabus and assignment pages sit only on the Instructor Guide's shelf,
    so it should rank first by a clear margin.  The Usage Guide's pages
    mention AI and students throughout, and they must not count, so this
    case also checks the threshold.

- id: H3
  pattern: own shelf wins
  guides: [student-guide]
  as: student
  turns:
    - "how do i get a copy of all my chats"
  expect:
    - never: [which_guide]
  passes_when: >
    Answers from its own files (exports are the Student Guide's).  The tool
    is for when the own search finds nothing; calling it on an in-scope
    question is the over-refusal family in a new form.

- id: H4
  pattern: zero everywhere
  guides: [student-guide, instructor-guide]
  as: student
  turns:
    - "Does the platform integrate with Gradescope?"
  expect:
    - any: [which_guide]
  passes_when: >
    Says it isn't in the documentation it has, and names the nearest thing
    its files cover.  Fails if it hands off to a guide with no matches, or
    invents an integration.

- id: H5
  pattern: desk routes on evidence
  guides: [welcome]
  as: nobody
  turns:
    - "what port does the admin panel listen on"
  expect:
    - calls: [which_guide]
  passes_when: >
    Sends them to the guide with the most matches in one or two lines.  On
    today's corpus the port is on two Operator Guide pages and two Security
    Guide pages, so a tie is likely: it names both and says which to open
    first.  Fails if it answers the question.
```

H3 is the one that keeps the tool honest.  A guide that calls `which_guide` before searching its own files has learned "hand off" as the safe move, and that is [the failure the fix can cause](agent-contract.md#the-failure-the-fix-can-cause) again.

## What this does not do

- **It doesn't answer the question.**  The receiving guide still searches and still cites its own files.
- **It doesn't make the directory obsolete.**  The directory still tells a guide what each sibling is for, and it is the fallback while `guide-index` is down.  If the tool errors, the guide routes on the directory, as it does today.
- **It doesn't see course documents.**  Instructors' knowledge files live in each course's own `rag-<slug>` store, which this never reads.

## Open questions

- **Gaps like the rate-limit one.**  A question that routes only to operator pages is often a reader-facing page that hasn't been written.  The tool's log will show them: a call where only the Operator, Platform and Security shelves count anything is a candidate, and that list is pedagogy's to read.
- **@marco:** does the service belong in its own container, or in `usage-mcp` with the rag_api image as its base?  Pedagogy has no preference.  The constraint is the credential: whatever hosts it must not hold `JWT_SECRET`.
- **Shelf overlap.**  Many pages sit on three or more shelves, so ties will be common once the caller's own count is zero.  The prompt names both on a tie.  If calibration shows ties on most hand-offs, the tool could count only pages unique to each guide, but that is a second change, not part of the first.
