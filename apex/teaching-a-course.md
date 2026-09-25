---
title: How do I teach a course on the aLLManac?
description: The faculty walkthrough — the day-zero checklist, the course patterns that work, and how to watch your course's spend, all from the browser.
audience: faculty
status: draft
owner: piper
tags: [sso, access-control, rbac, attribution, metering, assessment-design, ai-literacy, accountability, faculty-duty, student-right, librechat, backup, restore, retention]
tethered_to:
  - apex/user-guide.md
  - apex/your-data/how-long-we-keep-it.md
  - usage-mcp/server.py
  - registrar/server.py
  - registrar/planes/gateway.py
  - registrar/render.py
  - docs/admin-guide.md#backups
---

# Teaching a course on the aLLManac

*Everything here happens in the browser.*  You sign in with the same SSO button your students use, and the platform recognizes faculty — it hands you the sharing controls, the people picker, and your course's admin panel.  The panel lives next door to your course's chat: if students chat at `engr301.` followed by your campus domain, the panel is at `engr301-admin.` on the same domain, same SSO button.  Anything that needs a shell on the server is the admin's job, not yours; where that is the case below, it says so and tells you what to ask for.

Your students' own walkthrough is the [course guide](user-guide.md) — worth reading, because it is what they will be working from.

## Getting a course

**Ask for one at the front door.**  Tell the Instructor Guide you would like a course for your class.  It puts one question to you about the coursework first, then files your request as a ticket.  An admin approves it, sends it back with questions — you answer on the same ticket — or turns it down with a reason, and you are notified whichever way it goes.  Ask the guide where your requests stand (`my_requests`) any time.

You will not be asked for a budget.  The admins set it, which is also why the pool advice below is something to raise with them rather than a form to fill in.

## Day-zero checklist

1. **Everyone logs in once.**  Your students' accounts already exist — the roster creates them — so the first sign-in just links each person to theirs.  Make it the first five minutes of the first lab anyway: it is how you learn who is missing.
2. **Groups** (admin panel → Groups): one course-wide group (`engr301-all`), one per team (`engr301-team-gust`, ...).  These are groups in the chat platform's admin panel — the same SSO button, not the campus directory.  Membership edits propagate immediately, so late adds are painless; a student who cannot be found in the people picker has almost always not logged in yet.
3. **Keys**: nothing to hand out.  Enrolling a student mints their key, and they fetch it themselves by asking for it in your course's chat — see [Your API key](building-with-code/your-key.md).  Each one carries a modest budget of its own and the student's name.
4. **Verify one student end to end** — login, open a shared agent, paste a key into opencode — before the assignment goes out.

**If you want a key of your own, just ask for one in the chat.**  Ask your course's chat for your key (`my_key`) and it mints one the first time you ask — you, your TAs, and your students all draw from the same course pool, and every token any of you spends is metered to whoever spent it.  Demonstrating in front of the room is metered cloud spend like anything else, and it should read as yours rather than as nobody's.

**Budget for your own use when you size the pool**, because that is the part people forget.  Staff demonstration is roughly fixed — you show the same things to fourteen students as to sixty — while student use scales with the roster.  A pool sized only for the students starves the teaching.

**Know what happens when the pool runs out, because today it is everyone at once.**  The course pool is a ceiling on the whole course — chat and keys alike draw from it — and when it is spent, the course stops.  Not the student who spent the most: the student who opens their first assignment that evening, too.  Each key also carries its own smaller limit, so one runaway script hits its own wall long before it can empty the pool on its own; what empties a pool is a whole class running a little hot for a few weeks.  So watch the ledger (below) around the middle of term rather than the end, and if the numbers are trending past what you asked for, ask your admin to raise the pool before it runs dry rather than after.

One thing the roster does *not* decide is seniority.  It answers two separate questions: **who may change the roster** (instructors and TAs) and **who may hold a key** (everyone it names).  Those are unrelated, so put people where their job is rather than where their rank is — and for a course where *everybody* is learning, a staff cohort or a workshop or a reading group, the honest answer is usually one instructor and everyone else a student.

## Giving the platform your class list

**Paste it into your course chat.  Any format.**

First put the roster tools in reach — the same two clicks as [fetching a key](building-with-code/your-key.md): the course's own model from the picker, then **MCP Servers → almanac-registrar** in the message bar.  A course chat opens waiting for you to pick an agent, and without the registrar switched on it is only a chat.

You do not need to reformat anything, and there is no file to upload.  Export the roster from wherever you keep it — a CSV with eight columns, a list of addresses, an email you sent the section — paste the whole thing, and ask to stage a roster.  What matters is that the **sign-in email addresses** are somewhere in the text; headers, names, student numbers and junk columns are ignored, and you are told how many lines were skipped so you can tell "ignored the header" from "pasted the wrong column."

**Nothing changes when you paste.**  You get back exactly what would happen — who would be added, who would be removed, who is already enrolled — and the removals say plainly that those students' keys get revoked.  It changes only when you confirm, and the confirmation expires after fifteen minutes, so a paste you walk away from is not a change you come back to.

The two steps are `roster_stage` (show me what this would do) and `roster_apply` (do it).  Staff addresses in the paste are skipped rather than enrolled as students — you will not accidentally make yourself your own student by pasting a list you are on.

**A pasted list is the whole list.**  Anyone enrolled who isn't in the paste is on the removal side of the stage — which is right at the start of term and wrong for "add Pat."  For one or two people, ask to **enroll** or **unenroll** them by email instead: same stage, same confirmation, and nobody else is touched.  There is no command to memorize — "add these three: …" and "can you put Nia Okafor in my class? her email is …" both land on the same add-only preview.

**You don't have to be in the course to do this.**  The Instructor Guide at the front door can enroll people too — name the course and it works the same way.  Ask it "what am I teaching?" (`my_courses`) and it lists your courses with each one's chat address.

**Paste a big section in chunks of about forty.**  Each student is several operations behind the scenes, and a very large single paste can run long enough to look like nothing is happening.  It is safe either way — every step can be repeated without doing anything twice — but a paste that appears to hang is not a good first experience.  Re-pasting the same list is always safe: what is already enrolled stays enrolled.

## Adding a student to your class after it starts

Someone joins your section in week three, or switches in from another class.  Nothing about that is unusual and none of it is enrolment — the university admitted them long ago.  What they need is **access to your course**, and that is a roster change.

1. **Enroll them.**  In your course's chat, ask to enroll their sign-in email, read the stage, and confirm.  That creates their account, opens the door to your course, and mints their key in the same step — they do not have to have signed in first.  (They will not appear in the people picker until their first sign-in, which is the one place you might still notice the difference.)
2. **Add them to your course group** in the admin panel (admin panel → Groups → `engr301-all`, plus their team group if they have one).  Membership changes take effect immediately — there is no overnight sync to wait for.
3. **Tell them to fetch their key** if your course uses API keys for coding work.  It already exists — enrolling minted it — and they get it by asking your course's chat.  Nobody has to send it to them.

Removing someone who drops works the same way in reverse — ask to **unenroll** them, which closes their access and revokes their key in one step, then take them out of the group in the admin panel.

What you never do is send them to the Registrar's Office, and there is no LMS involved.  This is not the university's enrolment system; it is your course's access list, and it is yours to change.

## Course patterns that work

- **The course TA agent.**  You build it, attach the syllabus and lab manual, share **Viewer** to `engr301-all`.  Twenty questions about the late policy answer themselves.
- **Team-built agents as coursework.**  Each team gets Editor on their own agent (or creates it themselves — students can).  The assignment is the agent: instructions are graded prose, knowledge-file curation is graded research, and the iteration log is the lab notebook.
- **Peer review, course-wide.**  Teams share final agents to `engr301-all` as Viewer; classmates stress-test each other's work.  Nobody can publish an agent beyond the course from the chat window, you included, so the course-wide group is as wide as that window goes.  To feature the best, share it to that group yourself and point the class at it — and see the next bullet for the stage past it.
- **Nominating the best.**  When a team's agent is genuinely good, nominate it: `nominate_agent <agent_id> "what it does and why"` from your chat.  A platform admin turns it into a template file — instructions, model, tools, knowledge by name, the students' names on it as authors — that any course can seed.  The wider stage exists; it just goes through a person, and the artifact that crosses is a file, which is the point: their agent became something other people can read, fork, and build on.
- **Watching the ledger.**  In your course's chat, switch on **almanac-usage** under **MCP Servers** — the same menu as the registrar — and ask "how's engr301 tracking this month?", or the week-before-deadline favorite, "who hasn't started yet?"  The **Usage Guide** at the front door answers the same questions.  Totals, per-student activity listed by name, and the model mix, scoped to exactly your course.  (Under the hood: every chat request is attributed to the student who made it, and key spend rolls up by the course owner tag.)  That view is the whole of it on purpose: there is no dashboard login for instructors, because the analytics login sees every course's ledger, not just yours.
- **Term end.**  Ask the admin to sweep the course's keys.  Agents keep; keys retire.

## Something got deleted

The first thing to know is the part most people have backwards: **a backup is not an undo.**

A restore puts a whole database back to the moment a copy was made.  Getting your deleted agent back that way means putting the entire course back to that moment, and every conversation your students have had since goes with it.  Nobody trades a week of a class's work for one agent, so "can you restore just this thing" is almost always answered no — and it will still be answered no once the scheduled backups exist.  Backups are for the day the machine dies, not the day you click the wrong button.

What actually gets your work back is having kept it somewhere else.

- **Knowledge files.**  You uploaded them from somewhere, so upload them again.  That is the entire recovery, and it is the reason to keep the originals in a folder you control rather than only inside an agent.
- **An agent's instructions.**  An agent is a block of prose plus its files.  With the prose in hand, rebuilding is a few minutes of clicking — so keep a copy the way you keep a syllabus.  It is the same kind of document, and it is the part you actually wrote.
- **Conversations.**  These are the ones with no second copy anywhere.  If a thread is worth keeping, copy it out while it is still there.

If something is gone and it matters, **tell your admin the same day**, and name the thing and roughly when it went.  Whatever recovery is possible is bounded by how long any copy lives, and that clock started without you.

An honest note on where this platform actually stands: [How long we keep it](your-data/how-long-we-keep-it.md) is the current account, and today it is thin — copies are made by hand, there is no off-box schedule yet, and no restore has been exercised end to end.  Until that changes, plan as though recovery is your job, because mostly it is.

The almanac's rule is the farm's rule: everything gets written down, and the book stays on the shelf where the whole class can reach it.
