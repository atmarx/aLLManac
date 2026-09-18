---
title: How do I teach a course on the aLLManac?
description: The faculty walkthrough — the day-zero checklist, the course patterns that work, and how to watch your course's spend, all from the browser.
audience: faculty
status: draft
owner: piper
tags: [sso, access-control, rbac, attribution, metering, assessment-design, ai-literacy, accountability, faculty-duty, student-right, librechat]
tethered_to:
  - apex/user-guide.md
  - usage-mcp/server.py
---

# Teaching a course on the aLLManac

*Everything here happens in the browser.*  You sign in with the same SSO button your students use, and the platform recognizes faculty — it hands you the sharing controls, the people picker, and your course's admin panel.  The panel lives next door to your course's chat: if students chat at `engr301.` followed by your campus domain, the panel is at `engr301-admin.` on the same domain, same SSO button.  Anything that needs a shell on the server is the admin's job, not yours; where that is the case below, it says so and tells you what to ask for.

Your students' own walkthrough is the [course guide](user-guide.md) — worth reading, because it is what they will be working from.

## Day-zero checklist

1. **Everyone logs in once.**  Your students' accounts already exist — the roster creates them — so the first sign-in just links each person to theirs.  Make it the first five minutes of the first lab anyway: it is how you learn who is missing.
2. **Groups** (admin panel → Groups): one course-wide group (`engr301-all`), one per team (`engr301-team-gust`, ...).  These are groups in the chat platform's admin panel — the same SSO button, not the campus directory.  Membership edits propagate immediately, so late adds are painless; a student who cannot be found in the people picker has almost always not logged in yet.
3. **Keys**: hand the admin your roster; keys are minted with `owner=<your course>` and a per-student budget (the default is modest and adjustable).  Distribute via individual LMS messages.
4. **Verify one student end to end** — login, open a shared agent, paste a key into opencode — before the assignment goes out.

## Adding a student to your class after it starts

Someone joins your section in week three, or switches in from another class.  Nothing about that is unusual and none of it is enrolment — the university admitted them long ago.  What they need is **access to your course**, and that is a roster change.

1. **Add them to your roster.**  That creates their account and opens the door to your course in the same step — they do not have to have signed in first.  (They will not appear in the people picker until their first sign-in, which is the one place you might still notice the difference.)
2. **Add them to your course group** in the admin panel (admin panel → Groups → `engr301-all`, plus their team group if they have one).  Membership changes take effect immediately — there is no overnight sync to wait for.
3. **Ask your admin for a key** if your course uses API keys for coding work.  Send them the student's sign-in email and your course name; the key comes back minted against your course with the same per-student budget everyone else has.

Removing someone who drops works the same way in reverse — take them out of the group, and ask your admin to retire the key.

What you never do is send them to the Registrar's Office, and there is no LMS involved.  This is not the university's enrolment system; it is your course's access list, and it is yours to change.

## Course patterns that work

- **The course TA agent.**  You build it, attach the syllabus and lab manual, share **Viewer** to `engr301-all`.  Twenty questions about the late policy answer themselves.
- **Team-built agents as coursework.**  Each team gets Editor on their own agent (or creates it themselves — students can).  The assignment is the agent: instructions are graded prose, knowledge-file curation is graded research, and the iteration log is the lab notebook.
- **Peer review via the marketplace.**  Teams share final agents to `engr301-all` as Viewer; classmates stress-test each other's work.  Nobody can publish an agent beyond the course from the chat window, you included, so the course-wide group is the widest stage there is.  To feature the best, share it to that group yourself and point the class at it.
- **Nominating the best.**  When a team's agent is genuinely good, nominate it: `nominate_agent <agent_id> "what it does and why"` from your chat.  A platform admin turns it into a template file — instructions, model, tools, knowledge by name, the students' names on it as authors — that any course can seed.  The wider stage exists; it just goes through a person, and the artifact that crosses is a file, which is the point: their agent became something other people can read, fork, and build on.
- **Watching the ledger.**  Ask the **Almanac Usage** agent: "how's engr301 tracking this month?" — or the week-before-deadline favorite, "who hasn't started yet?"  Totals, per-student activity, and the model mix, scoped to exactly your course, in the same chat window.  (Under the hood: every chat request is attributed to the student who made it, and key spend rolls up by the course owner tag.)  Want raw dashboards instead?  Ask your admin for a read-only analytics login — it is one invitation link away.
- **Term end.**  Ask the admin to sweep the course's keys.  Agents keep; keys retire.

The almanac's rule is the farm's rule: everything gets written down, and the book stays on the shelf where the whole class can reach it.
