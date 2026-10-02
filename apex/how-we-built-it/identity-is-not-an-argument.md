---
title: Why the chatbot never asks who you are
description: If a tool takes a username as a parameter, the model can pass any username.  Identity has to arrive some other way — this is how, and why it matters the week you build your first agent.
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

You never told it your email address.  It never asked.  Look at the tool that answered, `my_usage` in `usage-mcp/server.py`, and the only thing it takes is a number of days.  There is no `user` parameter anywhere in it, and that is the most deliberate line in the file.

## The question

A tool that reports usage has to know whose usage to report.  Every tutorial on tool calling would hand it that as an argument.  Why doesn't this one take it?

## The obvious answer, taken seriously

`get_usage(user)`.  It is what every example shows, and it deserves a fair hearing: for most of what software does, it is a good design.

The schema documents itself — anyone reading the tool list knows exactly what it needs.  It is easy to test: call it with three different users and check three different answers.  You can call it from `curl` while debugging, with no session, no browser and no ceremony.  And the model is good at filling it in — "the user's email" is sitting right there in its context.

That last sentence is the whole problem, and it reads like a feature.

## What broke

**A tool parameter is filled by the model, and the model fills parameters from text in its context.**  The text in its context includes everything the person in the chat typed.  So a parameter named `user` is, in every sense that matters, a request for the model to be talked into a different value.

*"Show me the usage for dean@example.edu"* is not an attack that takes skill.  It is a sentence.  A model trained to be helpful will put that address in the `user` field, because that is what it was asked to do, and the tool — which has no way to know where the value came from — will answer.  You can add an instruction telling the model not to, and you have then moved your access control into a prompt, which is the one place guaranteed to be negotiable.

The general rule is older than language models: **anything the caller can type is an assertion, not an identity.**  It is the same reason a web application does not trust a `user_id` in a query string.  Models made it easier to get wrong: tool parameters look like function arguments and behave like user input.

There is a subtler trap waiting for whoever fixes it the obvious way.  The natural move is to take identity from the request instead of the arguments, and to prove the request came from a trusted caller with a bearer token in the `Authorization` header.  The MCP library this platform's tools are built on, `fastmcp`, hands you request headers through `get_http_headers()` — and strips `authorization` from what it returns unless you ask for it by name.  The function was designed for *forwarding* headers.  It is silent by design, and from the inside it looks exactly like a client that forgot to send the token.  Our check refuses when the token is missing, so the symptom was refusals pointing at the wrong side.  A check written the other way round — verify the token *if one is present* — would have turned the same quirk into no authentication at all, with no error.  It is written down as a wall (`docs/design-walls.md`, "fastmcp 3.x"), and both services ask for the header by name.

## What we did, and the bill

**Identity comes with the request, never the arguments.**  The chat software injects it.  Each LibreChat instance's configuration declares its tool servers with three headers, and LibreChat fills two of them per request from whoever is signed in:

```yaml
headers:
  Authorization: "Bearer ${USAGE_MCP_TOKEN}"
  X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
  X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
```

The bearer token proves the call came from the chat software and not from anything else on the network.  The email comes from the account that signed in through the institution's identity provider.  Neither passes through the model.  The model chooses *that* a tool is called and with *what* arguments; it has no say in the headers.

Every tool opens the same way — check the token, read the email, refuse if either is missing — and then scopes its answer by that email and nothing else.  Tools still take arguments: `my_usage` takes a number of days, and `course_usage` takes a course.  **A prompt can pick the date range.  It can never pick whose data comes back.**

Which course you are in can work the same way, with one more header.  A course instance's configuration is rendered by the registrar, and the registrar writes that course's id into it as a literal: `X-Course: "engr301-2026fall"`.  A tool called from inside that course knows which course it is serving because of a header nobody in the chat can edit.  The {{PLATFORM}} chat has no course, so it renders no `X-Course`, and the tools that are only about the room you are standing in refuse there, with no line of policy written anywhere.  The absence of a header is the access control.

Some tools *do* take a course as an argument, and the reason they can is the most transferable idea here.  An instructor can enrol students from the {{PLATFORM}} chat by naming the course, and anyone can ask the Coder Guide there for their API key, naming the course or letting the tool find their only one.  That is safe because the course argument only ever **chooses** which course — what **decides** whether you may touch it is the next line, a check of your injected email against that course's roster.  A student who names a course they aren't in gets no key, and a student who names a course to enrol people in gets the same refusal they would get inside it.  Keys moved to the {{PLATFORM}} chat for a dull reason: every tool attached to a course's chat is sent along with every turn of it, so bookkeeping there was billed to coursework.  The move cost nothing in safety, since the argument was only ever choosing.  Inside a course the header still wins, and a named course that disagrees with it is refused: the header is configuration the registrar rendered, and the argument is a model repeating what somebody typed.  The test for moving anything from header to argument is one question: **is it choosing, or deciding?**  Only the first can move.

The same rule applies at the meter.  Every chat request LibreChat sends to the gateway includes the signed-in email as `x-litellm-end-user-id`, so the ledger records who asked even though a course's chat runs on one shared service key.  A personal API key works the other way — the key is minted with your email as its owner, so whatever a script does with it is recorded against you without the script ever saying who you are.  Chat usage and key usage join on the same email, so `my_usage` can show both.

The bill:

- **The tools are harder to test.**  You cannot `curl` one with a username.  The probe we check them with on the box has to build the token and the headers by hand, and it asserts three things — the tool list returns, a scoped call works as a known user, and **a bad token is refused**.  That third one is the test that matters: the first two pass on a service with no authentication at all.
- **The injection path is security-critical**, and it lives in configuration: two config files, one hand-written and one rendered, each of which has to declare the headers correctly.  A misspelled placeholder arrives as the literal text `{{LIBRECHAT_USER_EMAIL}}`, so both services refuse an email that starts with `{{`.
- **The renderer is now part of the access control.**  If it ever wrote the wrong course id into an instance, every tool in that instance would serve the wrong course, correctly.

## What is still wrong with it

**The token used to say "a LibreChat", not "which LibreChat."**  Until 2026-10-02 there was one token per service, and every course instance held the same one, so anything that could present it could assert *any* email and *any* course.  Now each course gets its own, derived from a secret only the two services hold, and it is accepted only with that course's own `X-Course`.  The {{PLATFORM}} chat's token is refused if it names a course at all.  What remains is inside one course: its token can still assert any email in that course, because the email header is the only witness of who is asking.  A leaked course secret now reaches that course and no further, the same line [Keeping courses apart](keeping-courses-apart.md#what-we-did-and-the-bill) draws for the rest of a course's data.

**The headers are only as good as the sign-in.**  Every tool trusts the email LibreChat has for the signed-in account, and that came from the identity provider.  That is the right place for the chain to end, but it is where it ends: these tools add no check of their own, and a mistake upstream becomes a correct-looking answer about the wrong person.

**Getting identity right does not get scope right, and we have the receipt.**  Until 2026-10-01, `course_usage` — the instructor's view of a course — took the caller's identity exactly as described above and then picked rows by *person*: any ledger row whose user was one of the course's students.  A student's email is sent with every chat turn they make anywhere, so an instructor saw that student's activity in other courses and in the {{PLATFORM}} chat too, and "hasn't started yet" counted a student who had only worked in another course as started.  Nobody could ask for someone else's data.  The tool volunteered it.  The fix picks rows by the course instead — the course's team and its owner tag — and it turned up when a sweep of the site checked an instructor's page against the code — the page promised the view was "scoped to exactly your course."

That last gap is the one to remember.  **Out-of-band identity answers *who is asking*.  It says nothing about *which rows that person's question should touch*.**  Those are two decisions, and the second one gets made in a `WHERE` clause on an ordinary afternoon.

## Try it yourself

In the {{PLATFORM}} chat, ask the Usage Guide for a classmate's usage by their email address.  Watch what comes back: your own numbers, or a refusal, or the model explaining that the tool only answers for you.  What you will not get is theirs, and not because the model declined — there is nowhere in the request for their address to go.

Then ask it for `course_usage` on your own course.  Unless you teach it, you are refused, and the refusal names the roster, not your role.  The course you named was the *choosing* half.  Your email, which you did not type, was the *deciding* half.

Last, open `usage-mcp/server.py` in the repository and read the signatures: `my_usage(days: int = 7)`.  Then find `_ident()`, a short function that reads a token and two headers.  That function is the reason the chatbot never asks who you are — it already knows, and it never let the model have an opinion.

When you build your first agent with a tool of its own, write the signature before you write anything else, and ask of every parameter: *if a student typed a different value into the chat, would I mind?*  If the answer is yes, it is not a parameter.
