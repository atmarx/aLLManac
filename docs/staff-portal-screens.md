---
title: The staff portal's screens — what a person sees outside the chat
description: A build spec for the staff portal's pages outside the chat.  The intake's review-and-assert page and its receipt, the signed-in page that names who runs the system, and what a refusal looks like.  Mockups beside it in staff-portal-screens/.
audience: operator
status: proposed
owner: zoe
tags: [transparency-notice, access-control, accountability]
tethered_to:
  - docs/staff-portal.md
  - docs/staff-portal-counsel.md
---

# The staff portal's screens

A faculty member who has just told an assistant about a project gets a link.  Whatever opens next has one job before any other: tell them, in the first line they read, that nothing has been sent.  Every screen here starts from that kind of question: what does the person most need to know at this moment, and is it the first thing on the page?

This is the build spec for every screen in [staff-portal.md](staff-portal.md) that isn't a chat.  It is for @marco to build from.  The mockups are static HTML in [`staff-portal-screens/`](staff-portal-screens/index.html): open `index.html` in a browser.  They use the edge's own palette (`caddy/nocourse`) and need no script to read.

**Status: proposed, 2026-11-11.**  Words are placeholders until @piper writes them, and names are neutral placeholders.  `{{braces}}` are per-deployment slots, filled from `.env` the way `PLATFORM_NAME` is.

## Four rules every screen keeps

1. **Where you stand is the first line.**  Under the title, one boxed line says the state: *nothing has been sent*, *received, reference RC-…*, *correct as of…*.  Not a toast, not the bottom of the page.
2. **What a tool shows, the server shapes.**  When a tool's text is shown in the chat, it goes through the chat's markdown.  @geordi measured that 0.8.8 keeps tables but turns `$…$` into math, `^x^` into superscript and `:word` into a directive, so every string a tool renders is escaped for those characters.  The one path that shows a block unchanged is a tool that returns an HTML block (an MCP UI resource), in a sandboxed frame; it is the fallback, not the default.
3. **A test portal says so on every page.**  Each page opens with the banner.  The banner is a template switch, on for a test portal.
4. **No state is drawn as an error.**  A refusal is the system working.  No red, no warning icons.  Colour only repeats what the words already say.

## 1. Review and assert

Mockups: [`intake-review.html`](staff-portal-screens/intake-review.html) (mid-review, every field state on one page), [`intake-sent.html`](staff-portal-screens/intake-sent.html) (the receipt).

**Where it lives.**  Served by the draft-fields service at `/intake/d/<draft-id>` on the portal's chat host, the same origin as the chat, so the link the agent hands over stays on one host.  The service signs the person in itself, against the same issuer as the chat, so a person already signed in to the chat passes straight through ([staff-portal.md](staff-portal.md), "Where the decisions stand").  The draft ID is unguessable, but the boundary is the session: the page opens only for the draft's owner (session email equals the email LibreChat stamped when the agent created the draft).  Anyone else gets the wrong-account page in §3.  The agent's only part is to hand over the link.

**A field has four states**, and the page shows which one in words:

| State | Looks like | Moves to |
|---|---|---|
| Drafted, not confirmed | Editable control holding the draft, "Not confirmed", a **This is right** button | Confirmed |
| Changed, not confirmed | Same, plus "Changed from the draft" with the draft behind a disclosure and **Put the draft back** | Confirmed |
| Confirmed | Plain text, "Confirmed 9:41 pm", "as drafted" or "you changed the draft", an **Edit** link | Edit → back to unconfirmed |
| Not answered | Dashed border, empty control, "This didn't come up in your conversation" | Confirmed, if they fill it |

- **Each field is its own form posting to the server.**  The server records the value, `confirmed_at` from its own clock, and `changed` (final value differs from the agent's draft, whitespace-normalized).  That is counsel's whole list, and a client-side checkbox can't be trusted for "when".  Editing a confirmed field clears its confirmation.  With script on, the same posts go by `fetch` and the page doesn't reload; with script off, it still works.
- **Person-only fields.**  The rule's category is never drafted.  The field schema marks it `person_only`, the draft service refuses any agent write to it, and the page renders it with nothing selected and its options in the order the schema gives.  Where the person is being asked to classify (the rule's category), the options end with **None of them** and **I'm not sure, and I'd like the office to tell me**, set apart by a rule line.  Without that last option the page would push a person into classifying their own project, which is the office's job.  That tail comes from the field's `options_always_last`, not from the page, because a factual person-only field (where the proposal stands) has no "not sure".
- **A long form says where you are in it.**  The real list is thirteen fields.  The status line carries the count ("9 of 13 confirmed, 2 not answered"), and the assert sentence names the count it will send rather than a number written into the template.
- **Empty never blocks.**  The send box lists the fields that will go as "not answered", so nothing goes blank by surprise.  What blocks sending is only a field that holds a value nobody has confirmed, and the box links straight to each one.
- **One assert.**  The assert sentence sits directly above one checkbox and one button, both disabled (`aria-disabled`, with the outstanding list as the description) until nothing is outstanding.  No confirmation dialog after it: a second "are you sure?" teaches people to click through, and the page has already asked field by field.
- **Leaving is a first-class action.**  "Not now" goes back to the chat.  **Delete this draft now** deletes on the server at once and lands on "This draft is gone.  Nothing was sent."  The status line says when an unsent draft is deleted on its own.
- **After sending**, the same link shows the receipt and only the receipt: the reference, the time, what happens next, and every field exactly as the office got it, each with its confirmation mark.  No edits from here; a change goes to the office by email with the reference.  "Save a copy" is the browser's print, so the service writes no copy for the person.

**What I need from @marco:** the field schema carries `id`, `label`, `asks` (the help line), `kind` (`text` / `long` / `date` / `choice`), `person_only`, and for choices their options in order plus an optional `options_always_last` tail.  The draft carries per field `draft_value`, `value`, `confirmed_at`, `changed`.  The submission is assembled from those alone.

## 2. Who runs the system

Mockup: [`admins.html`](staff-portal-screens/admins.html).  Counsel's ruling ([staff-portal-counsel.md](staff-portal-counsel.md)): the portal's notice gives the administrators' roles and their number in one sentence, and links to a page that names them.  That page is **signed in**, because a public list of who administers a system is a target.  It is **not versioned**, because names change with staffing; it carries its own "correct as of" date.  It lives on the chat's own host beside the intake page, signs the person in the same way, and opens to anyone who can sign in to the portal.  If the roles or count here stop matching the notice, this page is the true one and the notice is owed a new version.

- **What they can read is said once, as measured.**  @geordi measured on 11-11 that the admin panel shows no one's chats and the engine refuses another person's chat to an admin.  So the sentence is that they can read the conversations where they are stored, to keep the system working.  It stays true only while nobody is mapped to the admin role day to day and the engine's insights view stays off ([staff-portal.md](staff-portal.md)).

## 3. A refusal

Mockup: [`refusal.html`](staff-portal-screens/refusal.html).

- **Three parts, in order:** what it won't do; the rule that stops it (never the person's fault); where to go instead.  A tool server writes those sentences itself and the model passes them on.  A refusal code handed to a model gets read aloud, so a code, if one exists for logs or evals, never reaches the model.
- **A refusal about a person's nationality offers nothing in its place.**  The explainer's first rule is that nothing about a person's nationality is said, ever.  Any alternative it could offer is the same question asked another way.
- **When a check can't be reached, the call is still refused, and the sentence says to try again shortly.**  Someone told "you aren't allowed" during an outage asks for access they don't need.
- **The wrong-account page** names the *viewer's* account, never the draft's owner, and says nothing about what the draft holds.  A missing, expired and deleted draft share one page: "This draft is gone.  Nothing was sent.  Start again from the chat."  A sent draft always shows its receipt, to its owner.

## Open, and whose

1. **Where the explainer's opening message appears, which waits on @xram's ruling on chat retention.**  The requirement: a person reads it before they type, on the view they land on, not behind a click or a collapsed panel, and it survives starting a new chat.  @geordi measured that a temporary chat replaces the landing view's description and greeting with the engine's own line.  If every chat expires after a set number of hours, the candidates stay the agent's description on its landing card and a model spec's greeting (plain text, not markdown), and what's left to measure is which shows first and how much each holds.  If the person chooses a temporary chat each time, the landing view can't carry it, and what remains is the chat's footer line (if it shows in a temporary chat at all) or a page before the chat, which reaches only a visit's first chat.  @geordi screenshots whichever form is ruled; I place the message from that, and @piper fits the words to the length.
2. **The category's options**, copied from the rule's primary text at the next corpus check.  The thirteen fields are written: research compliance keeps them outside this repository with the notes, and every kind in them fits the page as specified.  The mockup still draws six stand-ins.  @esmerelda
3. **Escaping in what the explainer's tools render** (`$`, `^`, `~`, `:` before a word), and an eval case that carries each.  Which escape survives 0.8.8's renderer is part of the job.  @marco
4. **The page where the office reads a submitted intake.**  Compliance's answer is that a submission stays in the service's own store and the office reads it on a signed-in page, with a message carrying only the reference ([staff-portal.md](staff-portal.md)).  Not drawn yet.  Mine, once the intake service's shape is settled.

**Settled:** an unsent draft lives seven days at most; the intake's pages and the administrators' page live on the chat's own host.
