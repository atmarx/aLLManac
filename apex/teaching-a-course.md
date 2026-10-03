---
title: How do I teach a course on {{PLATFORM}}?
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

# Teaching a course on {{PLATFORM}}

*Everything here happens in the browser.*  You sign in with the same SSO button your students use.  You're on your course's staff list, so the platform gives you your course's admin panel on top of the sharing controls and people picker everyone in the course has.  (Added to the list after you signed in?  Sign out and back in.)  The panel has its own address beside your course's chat: if students chat at `engr301.` followed by your campus domain, the panel is at `engr301-admin.` on the same domain, with the same SSO button.  Anything that needs a shell on the server is the admin's job; where that's the case below, you'll find what to ask for.

Your students work from the [course guide](user-guide.md), so read it too.

## Getting a course

**Ask the Instructor Guide in the {{PLATFORM}} chat.**  Tell it you'd like a course for your class.  It asks you one question about the coursework, then files your request as a ticket.  An admin approves it, sends it back with questions — you answer on the same ticket — or turns it down with a reason.  Where the platform has mail set up you get an email when it moves.  Either way, ask the guide where your requests stand (`my_requests`) and it shows the status and anything the admins wrote back.

You won't be asked for a budget.  The admins set it, so take the pool advice below to them.

## Day-zero checklist

1. **Everyone logs in once.**  Your students' accounts already exist — the roster creates them — so the first sign-in just links each person to theirs.  Make it the first five minutes of the first lab anyway: that's how you learn who is missing.
2. **Groups** (admin panel → Groups): one course-wide group (`engr301-all`), one per team (`engr301-team-gust`, ...).  These are groups in the chat platform's admin panel — the same SSO button, not the campus directory.  Membership edits propagate immediately, so late adds are painless; a student who cannot be found in the people picker has almost always not logged in yet.
3. **Keys**: nothing to hand out.  Enrolling a student mints their key, and they fetch it themselves by asking the **Coder Guide** in the {{PLATFORM}} chat — see [Your API key](building-with-code/your-key.md).  Each key has a modest budget of its own and the student's name on it.
4. **Verify one student end to end** — login, open a shared agent, paste a key into opencode — before the assignment goes out.
5. **Decide on conversation share links.**  By default, anyone in your course can make a link to one of their own conversations and send it to a classmate.  A link opens only for someone signed in to your course, never for the open web.  That helps when a student wants to show a TA a conversation that went wrong, and for peer review.  If it doesn't suit your course, turn it off in your course's admin panel: **Access → User → Shared links**, untick **Create**.  The setting stays as you leave it, including across restarts.

Want a key of your own?  Ask the **Coder Guide** in the {{PLATFORM}} chat for your key (`my_key`), naming the course if you teach more than one.  It mints one the first time you ask.  You, your TAs and your students all draw from the same course pool, and every token any of you spends is metered to whoever spent it.  A demonstration in front of the room is metered like anything else — in dollars on a hosted model, in tokens on a campus one — and it should show up under your name, not as nobody's.

Budget for your own use when you size the pool; it's the part people forget.  Staff demonstration is roughly fixed — you show the same things to fourteen students as to sixty — while student use grows with the roster.  A pool sized only for the students starves the teaching.

**When the pool runs out, today it runs out for everyone at once.**  The course pool is a ceiling on the whole course — chat and keys both draw from it — and when it's spent, the course stops.  That includes the student who opens their first assignment that evening, not only the one who spent the most.  Each key also has its own smaller limit, so one runaway script stops at that limit long before it can empty the pool; what empties a pool is a whole class running a little hot for a few weeks.  Watch the ledger (below) around the middle of term, not at the end, and if the numbers are trending past what you asked for, ask your admin to raise the pool before it runs dry.

The roster doesn't decide seniority.  It answers two separate questions: **who may change the roster** (instructors and TAs) and **who may hold a key** (everyone it names).  Those questions are unrelated, so put people where their job is, whatever their rank.  For a course where *everybody* is learning — a staff cohort, a workshop, a reading group — the usual answer is one instructor and everyone else a student.

## Giving the platform your class list

**Paste it into the Instructor Guide.  Any format.**

Open the **Instructor Guide** in the {{PLATFORM}} chat and tell it which course the list is for — or ask it "what am I teaching?" (`my_courses`) and pick from what comes back.  Roster work happens there and not in your course's chat, so bookkeeping never spends the course's budget or fills the course model's memory with tools your students' coursework doesn't use.

You do not need to reformat anything, and there is no file to upload.  Export the roster from wherever you keep it — a CSV with eight columns, a list of addresses, an email you sent the section — paste the whole thing, and ask to stage a roster.  What matters is that the **sign-in email addresses** are somewhere in the text; headers, names, student numbers and junk columns are ignored, and you are told how many lines were skipped so you can tell "ignored the header" from "pasted the wrong column."

**Nothing changes when you paste.**  You get back exactly what would happen — who would be added, who would be removed, who is already enrolled — and the removals say outright that those students' keys get revoked.  It's meant to change only when you confirm, and the confirmation expires after fifteen minutes, so a paste you walk away from is not a change you come back to.  **Read the plan before you type anything else.**  The assistant is told to wait for your yes, but until a check the platform is still building ships, only the assistant's own restraint stops it from applying straight away — a model once took *"just enroll these three instead"* as the yes.  If it ever applies without you confirming, report it.

The two steps are `roster_stage` (show me what this would do) and `roster_apply` (do it).  Staff addresses in the paste are skipped, not enrolled as students, so you can't make yourself your own student by pasting a list you're on.

**A pasted list is the whole list.**  Anyone enrolled who isn't in the paste is on the removal side of the stage — which is right at the start of term and wrong for "add Pat."  For one or two people, ask to **enroll** or **unenroll** them by email instead: same stage, same confirmation, and nobody else is touched.  There is no command to memorize — "add these three: …" and "can you put Nia Okafor in my class? her email is …" both get the same add-only preview.

One guide covers every course you teach.  Name the course each time, or let the guide ask; `my_courses` lists your courses with each one's chat address.

Paste a big section in chunks of about forty.  Each student is several operations behind the scenes, and a very large single paste can run long enough to look like nothing is happening.  It's safe either way — every step can be repeated without doing anything twice — but a paste that seems to hang is a bad first experience.  Re-pasting the same list is always safe: whoever is already enrolled stays enrolled.

## Adding a student to your class after it starts

Someone joins your section in week three, or switches in from another class.  Nothing about that is unusual, and none of it is enrolment — the university admitted them long ago.  What they need is **access to your course**, and that is a roster change.

1. **Enroll them.**  Ask the Instructor Guide to enroll their sign-in email in your course, read the stage, and confirm.  That creates their account, gives them access to your course, and mints their key in the same step — they don't need to have signed in first.  (They won't appear in the people picker until their first sign-in, the one place you might still notice the difference.)
2. **Add them to your course group** in the admin panel (admin panel → Groups → `engr301-all`, plus their team group if they have one).  Membership changes take effect immediately — there is no overnight sync to wait for.
3. **Tell them to fetch their key** if your course uses API keys for coding work.  It already exists — enrolling minted it — and they get it by asking the Coder Guide in the {{PLATFORM}} chat.  Nobody has to send it to them.

Removing someone who drops works the same way in reverse — ask to **unenroll** them, which closes their access and revokes their key in one step, then take them out of the group in the admin panel.

You never send them to the Registrar's Office, and there's no LMS involved.  This is your course's access list, not the university's enrolment system, and it's yours to change.

## Course patterns that work

- **The course TA agent.**  You build it, attach the syllabus and lab manual, share **Viewer** to `engr301-all`.  Twenty questions about the late policy answer themselves.
- **Team-built agents as coursework.**  Each team gets Editor on their own agent (or creates it themselves — students can).  The assignment is the agent: instructions are graded prose, knowledge-file curation is graded research, and the iteration log is the lab notebook.
- **Peer review, course-wide.**  Teams share final agents to `engr301-all` as Viewer; classmates stress-test each other's work.  Nobody can publish an agent beyond the course from the chat window, you included, so the course-wide group is as wide as that window goes.  To feature the best, share it to that group yourself and point the class at it — the next bullet covers the stage past that.
- **Nominating the best.**  When a team's agent stands out, nominate it: ask the Instructor Guide, with the agent's id (it's on the agent's edit page, `agent_…`) and a line on what it does and why.  A platform admin turns it into a template file — instructions, model, tools, knowledge by name, with the agent's creator named as its author and you named as the one who nominated it — that an operator can seed into any course.  (Students who co-edited it aren't named automatically; say so in the nomination.)  It's their work, so ask the team first, the way you would before reusing any assignment — the platform doesn't make you, and the template records that you sent it.  The wider stage exists; it just goes through a person, and what crosses is a file — their agent becomes something other people can read, fork and build on.
- **Watching the ledger.**  Ask the **Usage Guide** in the {{PLATFORM}} chat "how's engr301 tracking this month?", or the week-before-deadline favorite, "who hasn't started yet?"  Totals, per-student activity listed alphabetically by email, and the model mix, scoped to exactly your course.  (Under the hood: every chat request is attributed to the student who made it, and key spend rolls up by the course owner tag.)  That view is all there is, by design: instructors get no dashboard login, because the analytics login sees every course's ledger, not just yours.
- **Term end.**  The operator closes the course, which stops the spending but leaves sign-in open for 14 days so everyone can export their work; then archives it, which retires the keys and the chat.  Nothing is deleted.  [How long we keep it](your-data/how-long-we-keep-it.md#when-the-term-ends) has the detail students see.

## Something got deleted

Most people have this backwards: **a backup is not an undo.**

A restore puts a whole database back to the moment a copy was made.  Getting your deleted agent back that way means putting the entire course back to that moment, and every conversation your students have had since goes with it.  Nobody trades a week of a class's work for one agent, so "can you restore just this thing" is almost always answered no — and that stays true now that nightly backups run.  Backups are for the day the machine dies.  They won't help with a wrong click.

What gets your work back is having kept it somewhere else.

- **Knowledge files.**  You uploaded them from somewhere, so upload them again.  That's the whole recovery, and it's the reason to keep the originals in a folder you control as well as inside the agent.
- **An agent's instructions.**  An agent is a block of prose plus its files.  With the prose in hand, rebuilding is a few minutes of clicking — so keep a copy the way you keep a syllabus.  It's the same kind of document, and it's the part you wrote.
- **Conversations — and your agents, in one go.**  Ask the Instructor Guide to **export your data**: you get a zip of every conversation you had in the course and every agent you own, instructions included, behind a link good for 24 hours.  Do it before anything goes wrong, not after — it works on a closed or archived course too, but it can only export what is still there.

If something is gone and it matters, **tell your admin the same day**, and name the thing and roughly when it went.  Whatever recovery is possible is bounded by how long any copy lives, and that clock started without you.

Where the platform stands today: [How long we keep it](your-data/how-long-we-keep-it.md) has the current account, and it's half built.  A nightly backup copies everything off the machine, but the way back from it — a restore — is not built and has never been exercised.  Until that changes, plan as though recovery is your job, because mostly it is.

The rule here is an old one: everything gets written down, and the book stays on the shelf where the whole class can reach it.
