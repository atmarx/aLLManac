---
title: Can my course use its own tools?
description: Instructors can connect an outside tool server (MCP) to their course's chat and share it through an agent.  It starts closed — your operator opens it per course, one domain at a time.  Whatever the model sends that server leaves the platform.
audience: faculty
also_reaches: [builder, operator]
status: draft
owner: piper
tags: [tool-calling, egress-control, allowlist, data-processing-agreement, faculty-duty, librechat]
tethered_to:
  - registrar/render.py
  - registrar/planes/courses.py
  - scripts/egress-probe.js
  - docs/design-walls.md
---

# Can my course use its own tools?

A chemistry instructor wants the lab assistant agent to look up compounds in a database the department already runs.  A data-science course wants its agent to query a class dataset instead of a pasted CSV.  Both are reasonable, and both are what an **MCP server** is for: a small service that offers tools to a model — "search this catalog", "run this query" — so the agent can call them mid-conversation.

Yes, a course here can use one.  It takes one request to your platform operators, and a few decisions you should make before you send it.

## How it works in your course

As an instructor you're an administrator of your own course's chat, and the chat software lets administrators add an MCP server from the chat itself.  You give it a name and the server's address, and its tools become available to attach to agents.  Students can't add servers; they can only use what you share with them.

**Sharing an agent shares its tools.**  You don't share the server separately.  When you share an agent that uses the server's tools with your class, every student who opens that agent can run those tools, and the connection to the server is made as that student.

## It starts closed

Out of the box, your course's chat can't connect to any tool server outside the platform.  You can add one, but the chat refuses it when you save, with an error that the domain isn't allowed.

Whatever the model decides to send an outside tool server — a student's question, a pasted paragraph of their draft, part of a file — leaves the platform for someone else's computer.  Actions, the other way an agent can call the web, start closed for the same reason.

**To open it, ask your platform operators** for the server's domain to be added to your course.  Be ready to say:

- **What the server is and who runs it.**  Your department, a vendor, a public service, a colleague's research project.
- **What it will receive.**  What students will ask the agent, and so what the model is likely to pass along.
- **Whether that's allowed.**  If students' work goes to a third party, your institution's rules on sharing student records apply — the operators will ask whether there's an agreement with whoever runs the server.  [For instructors](your-data/for-instructors.md) covers the questions to settle first.

The operators add the domain to your course's record, and your course's chat picks it up at its next restart.  Only that course can connect to it, and only public hostnames qualify.  An address inside the platform's own network is refused.

## Before you attach it to an agent

- **Every tool costs tokens on every turn.**  A tool's description is sent with every message to an agent that has it, whether the student needs it or not.  A server with twenty tools can add thousands of tokens to each turn, which your course's budget pays for and which take room the conversation needs.  Attach the tools an agent needs, not the whole server.  ([Why the course chat no longer carries the platform's own tools](how-we-built-it/identity-is-not-an-argument.md) is the same lesson.)
- **Check what the server can do, not just what it says.**  A tool that can write, delete or send something will, when a student asks the right way.  Prefer read-only tools for a class.
- **Tell your students.**  Your syllabus policy should say that the agent can reach an outside service and what it sends there.  [Your syllabus policy](teaching-with-ai/syllabus-policy.md) has the shape.
- **Test it as a student would.**  Share the agent with a TA or a test account and ask it something real before the class sees it.

## If a tool goes quiet

If a domain is later removed from your course, servers at that domain stop working without an error.  The agent still lists the tools, and it answers without them.  If an agent that used to look things up starts guessing instead, ask your operators whether its server's domain is still on your course, and report it with the Student or Instructor Guide's report tool.

## The platform's own tools

Two tool servers come with every course: one reads usage numbers and one handles course business — keys, enrollment, exports.  Students and instructors use them through the guides in the {{PLATFORM}} chat; in a course chat they would spend the course's budget on bookkeeping.  They're still declared in your course, so you can attach them to an agent if you want one there.

---

**For operators:** a course's `mcp_domains:` list in `registrar/courses.yaml` takes public hostnames (`tools.example.org`, `*.example.org`, `https://host:port`), and `just course-check` refuses IP addresses, container names and localhost, because listing a host also lifts the chat software's private-address block for it.  Run `just render` after a change.  `just egress-check` asserts that every course refuses unlisted hosts and that the platform's own servers still connect.  The measured behavior behind all of this is in `docs/design-walls.md`, under "MCP servers staff add".
