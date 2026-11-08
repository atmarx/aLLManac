---
title: Can my course use its own tools?
description: Instructors can connect an outside tool server (MCP) to their course's chat and share it through an agent.  Outside servers are blocked by default, and your operator allows them per course, one domain at a time.  Whatever the model sends that server is sent outside the platform.
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

A chemistry instructor wants the lab assistant agent to look up compounds in a database the department already runs.  A data-science course wants its agent to query a class dataset instead of a pasted CSV.  Both are reasonable, and both are what an **MCP server** is for: a small service that offers tools to a model, such as "search this catalog" or "run this query", so the agent can call them mid-conversation.

A course on {{PLATFORM}} can use an MCP server.  Setting one up takes one request to your platform operators, and a few decisions you should make before you send it.

## How it works in your course

As an instructor you're an administrator of your own course's chat, and the chat software lets administrators add an MCP server from the chat itself.  You give the server a name and its address, and its tools become available to attach to agents.  Students can't add servers.  Students can only use the tools you share with them.

**Sharing an agent shares its tools.**  You don't share the MCP server separately.  When you share an agent that uses the server's tools with your class, every student who opens that agent can run those tools, and the connection to the server is made as that student.

## It starts closed

Out of the box, your course's chat can't connect to any tool server outside the platform.  You can add one, but the chat refuses to save it, with an error that the domain isn't allowed.

Anything the model sends to an outside tool server goes to someone else's computer, outside the platform.  That can include a student's question, a pasted paragraph of their draft, or part of a file.  Outside tool servers are blocked by default for that reason, and so are actions, the other way an agent can call the web.

**To allow an outside tool server, ask your platform operators** to add the server's domain to your course.  Be ready to tell them:

- **What the server is and who runs it.**  Your department, a vendor, a public service, a colleague's research project.
- **What it will receive.**  What students will ask the agent, and so what the model is likely to pass along.
- **Whether that's allowed.**  If students' work goes to a third party, your institution's rules on sharing student records apply.  The operators will ask whether there's an agreement with whoever runs the server.  [For instructors](your-data/for-instructors.md) covers the questions to settle first.

The operators add the domain to your course's record, and your course's chat starts allowing it at its next restart.  Only that course can connect to the domain, and only public hostnames qualify.  An address inside the platform's own network is refused.

## Before you attach it to an agent

Before you attach an outside tool server to an agent:

- **Every tool costs tokens on every turn.**  A tool's description is sent with every message to an agent that has the tool, whether the student needs it or not.  A server with twenty tools can add thousands of tokens to each turn.  Your course's budget pays for those tokens, and they take up room the conversation needs.  Attach only the tools an agent needs.  ([Why the course chat no longer carries the platform's own tools](how-we-built-it/identity-is-not-an-argument.md) is the same lesson.)
- **Check what each tool can do, beyond what its description says.**  If a tool can write, delete or send something, a student who asks the right way can make it do so.  Prefer read-only tools for a class.
- **Tell your students.**  Your syllabus policy should say that the agent can call an outside service and what it sends there.  [Your syllabus policy](teaching-with-ai/syllabus-policy.md) has the shape.
- **Test it as a student would.**  Share the agent with a TA or a test account and ask it something real before the class sees it.

## If a tool goes quiet

If a domain is later removed from your course, tool servers at that domain stop working without an error.  The agent still lists the tools, and it answers without them.  If an agent that used to look things up starts guessing instead, ask your operators whether its server's domain is still on your course, and report it with the Student or Instructor Guide's report tool.

## The platform's own tools

Two tool servers come with every course: one reads usage numbers, and one handles course business such as keys, enrollment, and exports.  Students and instructors use the platform's tool servers through the guides in the {{PLATFORM}} chat.  In a course chat, those tools would spend the course's budget on bookkeeping.  The platform's tool servers are still declared in your course, so you can attach them to an agent if you want them there.

---

**For operators:** a course's `mcp_domains:` list in `registrar/courses.yaml` takes public hostnames (`tools.example.org`, `*.example.org`, `https://host:port`), and `just course-check` refuses IP addresses, container names and localhost.  Listing a host also lifts the chat software's private-address block for it.  Run `just render` after a change.  `just egress-check` asserts that every course refuses unlisted hosts and that the platform's own servers still connect.  The measured behavior behind all of this is in `docs/design-walls.md`, under "MCP servers staff add".
