---
title: How do I teach a course on {{PLATFORM}}?
description: The faculty walkthrough, covering the day-zero checklist, the course patterns that work, and how to watch your course's spend, all from the browser.
audience: faculty
status: draft
owner: piper
tags: [sso, access-control, rbac, attribution, metering, assessment-design, ai-literacy, accountability, faculty-duty, student-right, librechat, backup, restore, retention, agent-design]
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

*Everything in teaching a course on {{PLATFORM}} happens in the browser.*  You sign in with the same SSO button your students use.  Because you're on your course's staff list, the platform gives you your course's admin panel, in addition to the sharing controls and people picker everyone in the course has.  If you were added to the staff list after you signed in, sign out and back in.  The admin panel has its own address next to your course's chat: if students chat at `engr301.` followed by your campus domain, the panel is at `engr301-admin.` on the same domain, with the same SSO button.  Anything that needs a shell on the server is the operators' job, and each task that needs one says what to ask the operators for.

Your students work from [Using it in a course](user-guide.md), so read it too.

## Getting a course

**To get a course, ask the Instructor Guide in the {{PLATFORM}} chat.**  Tell the guide you'd like a course for your class.  The guide asks you one question about the coursework, then files your request as a ticket.  An operator approves the request, sends it back with questions (you answer on the same ticket), or turns it down with a reason.  Where the platform has mail set up, you get an email when the request's status changes.  Either way, ask the guide where your requests stand (`my_requests`), and it shows the status and anything the admins wrote back.

You won't be asked for a budget when you request a course.  The operators set the course budget, so take the budget advice under [Day-zero checklist](#day-zero-checklist) to them.

## Day-zero checklist

1. **Everyone logs in once.**  The roster creates your students' accounts, so the first sign-in only links each person to their existing account.  Have everyone sign in during the first five minutes of the first lab anyway.  That is how you learn who is missing.
2. **Groups** (admin panel → Groups): one course-wide group (`engr301-all`), and one group per team (`engr301-team-gust`, ...).  These groups are in the chat platform's admin panel, which uses the same SSO button.  They are not campus directory groups.  Membership edits take effect immediately, so adding a student late is easy.  A student who can't be found in the people picker has almost always not logged in yet.
3. **Keys**: you have nothing to hand out.  Enrolling a student mints their key, and the student fetches it by asking the **Coder Guide** in the {{PLATFORM}} chat.  [Your API key](building-with-code/your-key.md) has the steps.  Each key has a modest budget of its own and the student's name on it.
4. **Verify one student end to end** before the assignment goes out: sign in, open a shared agent, and paste a key into a coding harness.
5. **Decide on conversation share links.**  By default, anyone in your course can make a link to one of their own conversations and send it to a classmate.  A share link opens only for someone signed in to your course, never for the open web.  Share links help when a student wants to show a TA a conversation that went wrong, and for peer review.  If share links don't suit your course, turn them off in your course's admin panel: **Access → User → Shared links**, uncheck **Create**.  The setting stays as you leave it, including across restarts.

Instructors can have an API key too.  To get your own key, ask the **Coder Guide** in the {{PLATFORM}} chat for your key (`my_key`), naming the course if you teach more than one.  The guide mints a key the first time you ask.  You, your TAs and your students all draw from the same course pool, and every token any of you spends is metered to whoever spent it.  A demonstration in front of the room is metered like anything else (in dollars on a hosted model, in tokens on a campus one), and it should be recorded under your name instead of under nobody's.

When you size the course pool, include your own use.  People often forget it.  Staff demonstration use is roughly fixed, since you show the same things to fourteen students as to sixty, while student use grows with the roster.  A pool sized only for the students leaves too little for teaching.

**Today, when the course pool runs out, it runs out for everyone at once.**  The course pool is a ceiling on the whole course.  Chat and keys both draw from it, and when it's spent, the course stops.  That includes the student who opens their first assignment that evening, not only the one who spent the most.

Each API key also has its own smaller limit, the key's fuse.  On a priced model, one runaway script stops at its key's fuse long before it can empty the course pool.  The fuse counts dollars, so on a model recorded at $0 it never moves ([your key](building-with-code/your-key.md#what-it-is) explains).  What empties a course pool is a whole class using a little more than planned for a few weeks.

If students' keys run out while the course pool still has room, ask your admin to raise the course's fuse.  The fuse is one number for every key in the course.  It can go as high as the platform's ceiling, and a raise applies to the keys students already hold, so nobody has to paste a new key.

Check the course ledger around the middle of term, not at the end.  "Watching the ledger" under [Course patterns that work](#course-patterns-that-work) shows how.  If the numbers are trending past what you asked for, ask your admin to raise the pool before it runs out.

The course roster does not record seniority.  The roster answers two separate questions: **who may change the roster** (instructors and TAs) and **who may hold a key** (everyone it names).  Those questions are unrelated, so list people by the job they do in the course, whatever their rank.  For a course where *everybody* is learning, such as a staff cohort, a workshop, or a reading group, the usual setup is one instructor and everyone else a student.

## Giving the platform your class list

**Paste your class list into the Instructor Guide, in any format.**

Open the **Instructor Guide** in the {{PLATFORM}} chat and tell it which course the list is for.  You can also ask it "what am I teaching?" (`my_courses`) and pick from the list it returns.  Roster work happens in the Instructor Guide instead of your course's chat.  That way bookkeeping never spends the course's budget, and never fills the course model's context with tools your students' coursework doesn't use.

You do not need to reformat the class list, and there is no file to upload.  Export the roster from wherever you keep it (a CSV with eight columns, a list of addresses, an email you sent the section), paste the whole thing, and ask to stage a roster.  The sign-in email addresses only need to appear somewhere in the text.  Headers, names, student numbers and junk columns are ignored.  The guide tells you how many lines were skipped, so you can tell "ignored the header" from "pasted the wrong column."

Pasting a class list changes nothing on its own.  The guide shows exactly what would happen: who would be added, who would be removed, and who is already enrolled.  The removals say that those students' keys get revoked.  The roster is meant to change only when you confirm, and the confirmation expires after fifteen minutes, so a paste you walk away from does not turn into a change later.  **Read the plan before you type anything else.**  The assistant is told to wait for your yes, but until a check the platform is still building ships, only the assistant's own restraint stops it from applying the change straight away.  A model once took *"just enroll these three instead"* as the yes.  If a roster change ever applies without you confirming, report it.

The two roster steps are `roster_stage` (show me what this would do) and `roster_apply` (do it).  Staff addresses in a pasted list are skipped and never enrolled as students, so you can't make yourself your own student by pasting a list you're on.

**A pasted list is the whole list.**  Anyone enrolled who isn't in the paste shows up as a removal in the stage.  That is right at the start of term and wrong when you only want to add Pat.  For one or two people, ask to enroll or unenroll them by email instead.  You get the same stage and the same confirmation, and nobody else is touched.  There is no command to memorize: "add these three: …" and "can you put Nia Okafor in my class? her email is …" both get the same add-only preview.

The Instructor Guide covers every course you teach.  Name the course each time, or let the guide ask.  `my_courses` lists your courses with each one's chat address.

To bring in a big section, ask the guide to enroll it in batches of about forty.  Enrolling only adds, so each batch leaves the earlier ones in place.  Pasting each batch as the class list would not work: every paste is the whole list, so the second batch would stage the first batch for removal.  Batches help because each student takes several operations behind the scenes, and a very large single request can run long enough to look like nothing is happening.  A large paste is still safe, since every step can be repeated without doing anything twice, but a paste that seems to hang is a bad first experience.  Re-pasting the same list is always safe: whoever is already enrolled stays enrolled.

## Adding a student to your class after it starts

A student may join your section in week three, or switch in from another class.  That is common, and it is not a university enrollment question: the university admitted them long ago.  What the student needs is **access to your course**, and that is a roster change.

1. **Enroll them.**  Ask the Instructor Guide to enroll their sign-in email in your course, read the stage, and confirm.  Enrolling creates the student's account, gives them access to your course, and mints their key in one step.  The student doesn't need to have signed in first.  They won't appear in the people picker until their first sign-in, which is the one place you might notice they haven't signed in yet.
2. **Add them to your course group** in the admin panel (admin panel → Groups → `engr301-all`, plus their team group if they have one).  Membership changes take effect immediately, with no overnight sync to wait for.
3. **Tell them to fetch their key** if your course uses API keys for coding work.  Enrolling already minted the key, and the student gets it by asking the Coder Guide in the {{PLATFORM}} chat.  Nobody has to send it to them.

Removing a student who drops works the same way in reverse.  Ask the Instructor Guide to **unenroll** them, which revokes their key at once and ends their chat access the next time the chat asks them to sign in.  Then take them out of the group in the admin panel.

Adding or removing a student never involves the Registrar's Office or an LMS.  The roster is your course's access list, not the university's enrollment system, and it's yours to change.

## Course patterns that work

- **The course TA agent.**  You build the agent, attach the syllabus and lab manual, and share it as **Viewer** to `engr301-all`.  The agent then answers the twenty questions about the late policy for you.
- **Team-built agents as coursework.**  Each team gets Editor on their own agent, or creates the agent themselves (students can).  The agent is the assignment: the instructions are graded as prose, the choice of knowledge files is graded as research, and the iteration log serves as the lab notebook.
- **Peer review, course-wide.**  Teams share final agents to `engr301-all` as Viewer, and classmates stress-test each other's work.  Nobody can publish an agent beyond the course from the chat window, you included, so the course-wide group is the widest sharing the chat window allows.  To feature the best agent, share it to that group yourself and point the class at it.  To share an agent beyond the course, see **Nominating the best**.
- **Nominating the best.**  When a team's agent stands out, you can nominate it.  Ask the Instructor Guide, giving the agent's id (it's on the agent's edit page, `agent_…`) and a line on what the agent does and why you're nominating it.  A platform admin turns the agent into a template file that an operator can seed into any course.  The template holds the agent's instructions, model, tools, and knowledge files by name.  It names the agent's creator as its author and you as the one who nominated it.  Students who co-edited the agent aren't named automatically, so say so in the nomination.
- **Asking the team before you nominate.**  A team's agent is the students' work, so ask the team before you nominate it, the way you would before reusing any assignment.  The platform doesn't require it, and the template records that you sent it.  A wider audience for an agent is possible, but it goes through a person, and what is passed on is a file: the team's agent becomes something other people can read, fork and build on.
- **Watching the ledger.**  Ask the **Usage Guide** in the {{PLATFORM}} chat "how's engr301 tracking this month?", or, the week before a deadline, "who hasn't started yet?"  The Usage Guide shows totals, per-student activity listed alphabetically by email, and the model mix, limited to your course.  Every chat request is attributed to the student who made it, and key spend is totaled by the course owner tag.  The Usage Guide is the only view instructors get.  There is no dashboard login for instructors, because the analytics login sees every course's ledger, not just yours.
- **Term end.**  At term end, the operator closes the course.  Closing stops the spending but leaves sign-in open for 14 days so everyone can read back through their work.  The operator then archives the course, which retires the keys and the chat.  Nothing is deleted.  [How long we keep it](your-data/how-long-we-keep-it.md#when-the-term-ends) has the detail students see.

## Something got deleted

**A {{PLATFORM}} backup is not an undo for one deleted item.**

A restore puts the whole platform, every course included, back to the moment a copy was made.  [Backups](your-data/how-long-we-keep-it.md#backups) explains how backups work.  Because a restore resets everything, the answer to "can you restore just this thing" is almost always no.  Backups are for the day the machine dies, and they won't help with a wrong click.

To get deleted work back, you need your own copy kept somewhere else.  Each kind of work has its own way to keep a copy:

- **Knowledge files.**  To recover a knowledge file, upload the original again.  Keep the originals in a folder you control as well as inside the agent, so you always have them to upload.
- **An agent's instructions.**  An agent is a block of written instructions plus its files.  With the instructions in hand, rebuilding an agent takes a few minutes of clicking.  Keep a copy of an agent's instructions the way you keep a copy of your syllabus.
- **Conversations and agents, in one export.**  Ask the Instructor Guide to **export your data**.  You get a zip of every conversation you had in the course and every agent you own, instructions included, behind a link good for 24 hours.  Export before anything goes wrong.  The export works on a closed or archived course too, but it can only export what is still there.

If something important is deleted, **tell the operators the same day**, and name what was deleted and roughly when.  Any recovery is limited by how long copies are kept, and that time started counting before you noticed the loss.

Today, {{PLATFORM}} backups run nightly, and a restore is not built yet.  [Backups](your-data/how-long-we-keep-it.md#backups) has the current status.  Until a restore exists, plan as though recovering your work is your job.  For now, it mostly is.
