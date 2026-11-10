---
title: Why the chatbot never asks who you are
description: If a tool takes a username as a parameter, the model can pass any username.  How this platform gives tools the user's identity instead, and why that matters when you build your first agent.
audience: builder
also_reaches: [student]
status: draft
owner: piper
tags: [attribution, access-control, least-privilege, audit-logging, tool-calling, librechat, litellm]
tethered_to:
  - usage-mcp/server.py
  - registrar/server.py
  - registrar/render.py
  - librechat/librechat.yaml
  - docs/design-walls.md
---

# Why the chatbot never asks who you are

Open the Usage Guide in the {{PLATFORM}} chat and type *"how much have I used this week?"*  The answer comes back with your email address at the top of it.

You never told the Usage Guide your email address, and it never asked.  The tool that answered is `my_usage` in `usage-mcp/server.py`, and its parameters only pick a window of time: a number of days, or a calendar month.  There is no `user` parameter anywhere in `my_usage`, and that is intended.

## The question

A tool that reports usage has to know whose usage to report.  Most tutorials on tool calling would pass that as an argument.  So why doesn't `my_usage` take one?

## The obvious answer, taken seriously

The obvious design is `get_usage(user)`.  Most examples show it, and for most software it is a good design.

A `user` parameter documents itself: anyone reading the tool list knows what the tool needs.  It is easy to test: call it with three different users and check three different answers.  You can call it from `curl` while debugging, with no session and no browser.  And the model is good at filling it in, since the user's email is already in its context.

The model filling in the user is exactly the problem.

## What broke

The model fills in tool parameters from text in its context, and that text includes everything the person in the chat typed.  So anyone in the chat can try to talk the model into putting a different value in a parameter named `user`.

Typing *"Show me the usage for dean@example.edu"* takes no skill.  A model trained to be helpful will put that address in the `user` field, and the tool has no way to know where the value came from, so it will answer.  You can add an instruction telling the model not to, but then your access control is a prompt, and anyone can argue with a prompt.

The general rule is older than language models: **anything the caller can type is an assertion, not an identity.**  A web application does not trust a `user_id` in a query string for the same reason.  Language models make the mistake easier, because tool parameters look like function arguments but behave like user input.

The obvious fix has its own trap.  The usual fix is to take identity from the request instead of the arguments, and to prove the request came from a trusted caller with a bearer token in the `Authorization` header.  The MCP library this platform's tools are built on, `fastmcp`, returns request headers through `get_http_headers()`, but it strips `authorization` from the result unless you ask for that header by name.  The function was designed for forwarding headers, and it drops `authorization` without any warning.  From inside the tool, that looks exactly like a client that forgot to send the token.

The platform's token check refuses when the token is missing, so the `fastmcp` header stripping showed up as refusals that seemed to be the client's fault.  A check written the other way around, one that verifies the token only *if one is present*, would have turned the same quirk into no authentication at all, with no error.  The behavior is recorded as a design wall (`docs/design-walls.md`, "fastmcp 3.x"), and both services ask for the header by name.

## What we did, and the bill

On this platform, identity comes with the request and never from the tool arguments.  The chat software adds it.  Each LibreChat instance's configuration declares its tool servers with three headers, and LibreChat fills in two of them on each request from the signed-in account:

```yaml
headers:
  Authorization: "Bearer ${USAGE_MCP_TOKEN}"
  X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
  X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
```

The bearer token proves the call came from the chat software and not from something else on the network.  The email comes from the account that signed in through the institution's identity provider.  Neither value passes through the model.  The model decides *whether* a tool is called and with *what* arguments.  It has no control over the headers.

Every tool starts the same way: check the token, read the email, and refuse if either is missing.  Then it scopes its answer by that email and nothing else.  Tools still take arguments: `my_usage` takes a number of days or a month, and `course_usage` takes a course and the same window.  **A prompt can pick the date range, but it can never pick whose data comes back.**

The current course can be passed the same way, in one more header.  The registrar renders each course instance's configuration and writes that course's id into it as a literal: `X-Course: "engr301-2026fall"`.  A tool called from inside that course knows which course it is serving from a header nobody in the chat can edit.  The {{PLATFORM}} chat has no course, so its configuration has no `X-Course` header.  Tools that only work on the current course refuse there, and no extra policy code is needed.

Some tools *do* take a course as an argument, and the reason that is safe applies well beyond this platform.  An instructor can enroll students from the {{PLATFORM}} chat by naming the course, and anyone can ask the Coder Guide there for their API key, naming the course or letting the tool find their only one.  The course argument only *chooses* which course.  The next line of the tool *decides* whether you may touch it, by checking your injected email against that course's roster.  A student who names a course they aren't in gets no key, and a student who names a course to enroll people in gets the same refusal they would get inside it.

The key tools moved to the {{PLATFORM}} chat for a practical reason: every tool attached to a course's chat is sent along with every turn of that chat, so key bookkeeping there was billed to coursework.  The move cost nothing in safety, since a course argument only chooses.  Inside a course chat, the `X-Course` header still wins, and a named course that disagrees with it is refused.  The header is configuration the registrar rendered, and the argument is a model repeating what somebody typed.  Before moving anything from a header to an argument, ask one question: **is it choosing, or deciding?**  Only a value that chooses can move.

Usage metering follows the same rule.  Every chat request LibreChat sends to the gateway includes the signed-in email as `x-litellm-end-user-id`, so the ledger records who asked even though a course's chat runs on one shared service key.  A personal API key works differently.  The key is minted with your email as its owner, so whatever a script does with it is recorded against you, and the script never has to say who you are.  Chat usage and key usage are recorded under the same email, so `my_usage` can show both.

The costs of passing identity in headers:

- **The tools are harder to test.**  You cannot `curl` one with a username.  The probe we check them with on the box has to build the token and the headers by hand, and it checks three things: the tool list returns, a scoped call works as a known user, and a bad token is refused.  The third check is the important one, since the first two also pass on a service with no authentication at all.
- **The injection path is security-critical**, and it is set in configuration: two config files, one hand-written and one rendered, each of which has to declare the headers correctly.  A misspelled placeholder arrives as the literal text `{{LIBRECHAT_USER_EMAIL}}`, so both services refuse an email that starts with `{{`.
- **The renderer is now part of the access control.**  If it ever wrote the wrong course id into an instance, every tool in that instance would serve the wrong course, and every check would pass.

## What is still wrong with it

**The tool token used to prove only that a call came from some LibreChat instance, not which one.**  Until 2026-10-02 there was one token per service, and every course instance had the same one, so anything that could present it could assert *any* email and *any* course.  Now each course gets its own token, derived from a secret only the two services hold, and it is accepted only with that course's own `X-Course`.  The {{PLATFORM}} chat's token is refused if it names a course at all.

A course's tool token can still assert any email, because the email header is the only evidence of who is asking.  So since 2026-10-23, no tool lets a course named in an argument take a call outside the course it came from.  Inside a course chat, the course in the header wins over the one in the argument, and the operators' tools answer only in the {{PLATFORM}} chat.  A leaked course secret now exposes that course and no other, the same boundary [Keeping courses apart](keeping-courses-apart.md#what-we-did-and-the-bill) draws for the rest of a course's data.

**The headers are only as good as the sign-in.**  Every tool trusts the email LibreChat has for the signed-in account, and that email came from the identity provider.  The identity provider is the right place for the chain of trust to end, but the chain does end there: the tools add no check of their own.  A mistake upstream becomes a correct-looking answer about the wrong person.

**Getting identity right does not get scope right, and this platform made that mistake.**  Until 2026-10-01, `course_usage` (the instructor's view of a course) got the caller's identity from the headers and then picked rows by *person*: any ledger row whose user was one of the course's students.  A student's email is sent with every chat turn they make anywhere.  So an instructor saw that student's activity in other courses and in the {{PLATFORM}} chat too, and "hasn't started yet" counted a student who had only worked in another course as started.  Nobody could ask for someone else's data, but the tool returned it anyway.  The fix picks rows by the course: the course's team and its owner tag.  The bug was found when a sweep of the site checked an instructor's page against the code.  That page promised the view was "scoped to exactly your course."

The `course_usage` bug shows a general rule.  **Out-of-band identity answers *who is asking*.  It says nothing about *which rows that person's question should touch*.**  Those are two separate decisions, and the second one is made in an ordinary `WHERE` clause.

## Try it yourself

In the {{PLATFORM}} chat, ask the Usage Guide for a classmate's usage by their email address.  You will get your own numbers, a refusal, or the model explaining that the tool only answers for you.  You will not get your classmate's numbers.  The model did not make that decision: the request has no field where their address could go.

Then ask the Usage Guide for `course_usage` on your own course.  Unless you teach it, you are refused, and the refusal cites the roster, not your role.  The course you named did the *choosing*.  Your email, which you did not type, did the *deciding*.

Last, open `usage-mcp/server.py` in the repository and read the signatures: `my_usage(days: int = 7, month: str = "")`.  Then find `_ident()`, a short function that reads a token and two headers.  `_ident()` is why the chatbot never asks who you are: the tool already has your identity from the headers, and the model has no way to change it.

When you build your first agent with a tool of its own, write the tool's signature first.  For every parameter, ask: *if a student typed a different value into the chat, would I mind?*  If the answer is yes, that value should not be a parameter.
