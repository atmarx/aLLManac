---
title: The staff portal's program rules — retention, what the explainer may promise, and who administers it
description: Counsel's positions for the staff portal's chat, the chat's retention and the sentences the explainer may promise, who administers the portal, and the explainer's opening message.  Positions for the operator to adopt.
audience: operator
status: proposed
owner: nora
tags: [transparency-notice, retention, secure-deletion, data-minimization, accountability]
tethered_to:
  - docs/staff-portal.md
  - docs/staff-portal-screens.md
  - docs/staff-portal-agents.md
---

# The staff portal's program rules

What a person is told before they type, and how long what they type lives.  This page is counsel's positions, written for @piper to voice and @geordi to verify against the chat engine.

**Status: proposed, 2026-11-11.**  These are counsel's positions.  The institution's own counsel signs whatever a real deployment adopts.  Numbers marked *placeholder* wait on the institution's records schedule.  Nothing here is legal advice, and an institution's published guidance outranks it.  Section numbers are kept from the page's first form so that citations hold.

The institution, its offices and its people are slots, filled from `.env` and `site/` as [customizing.md](customizing.md) describes: `{{INSTITUTION}}`, `{{COMPLIANCE_OFFICE}}`, `{{CONTACT}}`.

## 4. Retention

Ruled by @xram (11-11): nothing is kept unless the person chooses to keep it.  The chat engine's own documentation (read by @esmerelda, 11-11, not yet measured on the pinned version) says that cannot be said in those words: a temporary chat is stored on the server until its retention period ends, the shortest period is one hour, the default mode lets the person choose chat by chat, and no documented mode makes a chat temporary *unless the person keeps it*.  So there is a transcript window after all, and it is an hour.

**Counsel's position on the mode: the server's deadline, not the person's switch (revised 11-11, after the measurement).**  My first recommendation was to lock every chat to temporary.  @geordi's reading of the pinned engine (`b8cbe30`) says no setting does that: "temporary by default" is a switch in the person's own browser, and the server can only remove the temporary option.  So the choice @esmerelda lays out is (a) temporary chats the person turns on, or (b) `retentionMode: all`, where every chat gets a deadline the server sets.  I recommend (b), with search off.  The ruling is that nothing is kept unless the person chooses to keep it.  Under (a) a person who forgets the switch has made a record that stays until they delete it, and the people who most need the protection are the ones who forget.  Under (b) the server deletes every chat on schedule, nobody has to remember anything, and with search off the one flaw measured in (b), text surviving in the index after expiry, does not exist.  The costs are real and the notice says them: a chat is listed in the person's own history until it expires, and the opening message stays where it is, which is better than (a), where the engine replaces it.  Two things to settle with the number.  The deadline under (b) is stamped once, when the chat is started, not after the last message, so a long conversation ends at the deadline whatever the person is doing.  Counsel has nothing to set at one hour and can accept up to one working day if one hour breaks real use, and a longer period changes the notice sentence, not the ruling.  The admin panel and admin API show no one's chats, and Insights, the one route that would, stays off.  The mode and the number are @xram's.

The rest of this section is what remains.

| Thing | Kept | Who may delete it |
|---|---|---|
| A chat | Under (b), deleted the ruled number of hours after the chat was started (one hour is the shortest the engine allows), listed in the person's own history until then, and not searchable because search is off.  Under (a), a chat the person did not mark temporary is kept until they delete it | The engine, by expiry.  The person, earlier |
| An unsent intake draft | Seven days at most, then deleted.  Shorter is better; this is the conversation in another shape | The person, or expiry |
| A submitted intake | As an institutional record, under {{COMPLIANCE_OFFICE}}'s records schedule | Not by the person through the chat.  The review page says so before the assert button |
| Backups | Expire within a stated number of days (the number is @geordi's to state) | Expiry |

### What the explainer may promise

The explainer opens by saying the conversation is not kept.  Each sentence it says has to be true of every copy, so each has a person who verifies it before it ships:

| Sentence | True only when | Verified by |
|---|---|---|
| Under (b): "This conversation is deleted from the server {{CHAT_RETENTION_PERIOD}} hours after it starts, even if you are still using it.  Until then it is listed in your history.  Copies in the server's backups expire within {{BACKUP_DAYS}} days." (@piper's draft, `09a6de9`, with the backup clause joined to it.)  The earlier "no one else's" is out: it overclaims, since the operator with the database can read a chat that exists | `retentionMode: all` at that number, search off, and the backup number measured.  "Deleted from the server" is never said without the backup clause in the same breath | @geordi, on 0.8.8, by trying it |
| "Copies in the server's backups expire within {{BACKUP_DAYS}} days." | The backup holds conversations at all, and the number is the expiry | @geordi.  If backups hold the conversation database, "deleted" is not said until the number is |
| "Nothing here is saved to a memory." | Memories are off.  A memory saved in a temporary chat outlives it, so this is the setting that makes the sentence true | @geordi |
| "Nothing you type here is kept unless you save it." | **Never ships.**  Under the engine's documented modes it is false: either every chat expires or the person must opt in to expiry | Retired |
| "Nobody at {{INSTITUTION}}, including {{COMPLIANCE_OFFICE}}, can read this conversation." | The admin view shows nothing of another person's chat | @geordi |
| "The model provider does not keep what you type." | The agreement says so for this tenant | Whoever holds the agreement, in writing.  @xram has said the tenant keeps no prompts; nobody on this project has read the terms |
| "Exploring a hypothetical creates no record at {{COMPLIANCE_OFFICE}}." | Only a submitted intake leaves the chat, and only fields the person confirmed | @marco |
| "Deleting a chat does not withdraw a submission." | Always true.  Say it | This page |

A sentence with no verifier is left out of the opening message, not softened.  If the provider sentence cannot be verified, the message says only what is true: "Our model provider may keep metadata about each request."

## 5. Rulings after the faculty read (2026-11-11)

**The people who administer the system.**  They are named in the portal's notice, in one sentence under "Who can look", and the explainer's opening message points at that sentence.  The sentence carries the roles and the count, and links to a signed-in page that names the holders.  The notice stays public and versioned; the list of names changes with staffing and doesn't belong in a versioned page, and a public list of who administers the system is a target.  The signed-in page has its own date.  The notice is the page people read, so it carries the sentence and the link, and the explainer is not the only place the fact lives.

**The explainer's opening message.**
- **Paragraph one** leads with the true sentence.  What the people who run the system can reach is stated as @geordi measures it: "can read" if the admin panel can show a conversation, "can technically reach" only if it cannot.  The reassurance follows the fact, never the other way.  "Nobody reads it" stays out until someone can verify it as practice; "no one at {{INSTITUTION}} is given a copy" is the verifiable form.
- **The provider sentence.**  "May keep metadata about each request" is a softening and is out.  Two forms are allowed.  *Verified:* the plain sentence of what is kept and what is not ("The provider logs that a request happened and its size and time, not what you typed"), shipped when whoever holds the agreement confirms it in writing.  *Unverified:* "We haven't confirmed how long our model provider keeps what you type.  Until we do, write nothing here you wouldn't put in an email."  @xram has stated the tenant keeps no prompts; that goes in the board record as the statement it is, and the verified form waits on the agreement.
- **A fifth office in the routing**, for publication or access restrictions in a sponsor's terms.  Counsel agrees with the faculty read.  It is a routing slot, so it's @esmerelda's to fill.

## What this page leaves open

1. **The records schedule.**  The institution's schedule supplies the period for a submitted intake.
2. **Foundry's terms.**  @xram has stated that the tenant keeps no prompts.  Someone who holds the agreement reads it before the first faculty member types a project description.
3. **The chat mode and number** (@xram): (a) temporary by the person's choice, or (b) every chat on the server's deadline.  There is no lock.  Counsel recommends (b) with search off.
