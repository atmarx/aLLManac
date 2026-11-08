---
title: How do you protect data you can't delete?
description: Course data comes with obligations that outlast the term.  Which regime attaches to which data, why classification is a decision someone with authority registers, and what running the platform yourself changes.
audience: builder
also_reaches: [faculty]
status: draft
owner: piper
tags: [ferpa, gdpr, nist-800-53, nist-800-171, cui, fisma, data-classification, high-risk-data, education-record, retention, secure-deletion, backup, data-processing-agreement, faculty-duty]
regimes: [ferpa, gdpr, nist-800-53, nist-800-171]
tethered_to:
  - justfile
  - docs/admin-guide.md#backups
  - registrar/reconcile.py
  - registrar/planes/verbs.py
  - registrar/planes/exports.py
  - litellm/config.yaml
---

<!-- COUNSEL BOUNDARY.  This page describes regimes in general terms and
     describes our system factually.  It makes no compliance claim about this
     platform and gives no legal advice.  Counsel review is required before
     status: published, and the external sources in beat 3 and beat 4 need a
     citation pass first. -->

# How do you protect data you can't delete?

The email arrives in May, a week after grades post.  *"Please delete everything I typed into the course chat this term."*

The request is reasonable.  It contains three questions: whether anybody is obliged to delete the data, whether anybody is allowed to, and whether the system can.  The third question is the easiest, and it is the one engineers start with.

## The question

A course on this platform produces three kinds of record about named people: the conversations, both sides of them; the files students and instructors uploaded; and the usage records (which model, how many tokens, when, against whose key).  The records remain after the term ends.

So who is allowed to read course records, how long do they stay, and what happens when someone asks for a copy, or asks for them to be deleted?

[How long we keep it](../your-data/how-long-we-keep-it.md) and [Asking about your data](../your-data/asking-about-your-data.md) answer those questions for students, including the list of gaps.  For builders, the useful part is how those answers were decided, and what deciding them cost.

## The obvious answer, taken seriously

*Encrypt everything, lock it down, delete it when they ask.*

Encrypting, locking down, and deleting on request are good instincts, and a team that does all three is ahead of most.  Each one needs more detail than it first appears to:

- **Encrypt what, against which threat, and who holds the key?**  Disk encryption protects a drive that walks out of the building.  It does nothing about the operator, who runs the machine with the drive unlocked, or about a backup copied somewhere with its key beside it.
- **Lock it down from whom?**  The people with the most access to course data are the people running the servers.  "Locked down" has to say something about them, or it says very little.
- **Delete it when, and on whose authority?**  Deletion looks like an engineering task, but it is a legal question first, as [What broke: the assumption, not the system](#what-broke-the-assumption-not-the-system) explains.

## What broke: the assumption, not the system

Nothing in the system broke here.  What broke was an assumption almost everyone starts with, about what the privacy laws require.

**FERPA is not an erasure regime.**  It gives students the rights to inspect, amend, consent to disclosure and complain ([the full list](../your-data/asking-about-your-data.md#what-ferpa-gives-you)), and no delete-my-data right.  Engineers expect one, because GDPR's Article 17 and the state consumer privacy laws trained the instinct on consumer products.  A team that builds a deletion pipeline "for FERPA" is satisfying a requirement FERPA never stated, and quite possibly missing the ones it did.

The federal security frameworks are not triggered by student data either.  NIST SP 800-53 is the control catalog for federal information systems under FISMA.  NIST SP 800-171 covers Controlled Unclassified Information in nonfederal systems, and it applies by *contract*: a DFARS clause, or similar language flowed down from a federal sponsor.  So colleagues in sponsored research deal with NIST SP 800-171, and a teaching platform usually does not.  Neither framework attaches because student data is sensitive.

Course data is governed by less famous, more local rules: FERPA, the state student-privacy statutes (well over a hundred of them, and many *do* impose retention and deletion duties FERPA does not), and the institution's own data classification policy, which is the one that binds day to day.

**The trigger for a regime is usually data type plus contract, not a general duty to be secure.**  An engineer who learns to ask *"what makes this regime apply to me?"* stops applying the wrong one.

Wrong answers about FERPA and AI tools are also easy to find:

- **"There is no such thing as a 'FERPA seal of approval.'"**  That is Michael Hawes, a former director of the Department of Education's Student Privacy Policy and Assistance Division, as quoted in the Future of Privacy Forum's [*Vetting Generative AI Tools for Use in Schools*](https://fpf.org/wp-content/uploads/2024/10/Ed_AI_legal_compliance.pdf_FInal_OCT24.pdf) (April 2024).  FERPA binds the institutions that receive federal funding and reaches the companies that sell to them only through those institutions, so no product can *be* FERPA-compliant.  The real question is whether an institution can use it in a compliant way.  Search for "FERPA-compliant AI" anyway and most of the results are selling something that cannot exist.
- **Most of the available guidance is shaped for K-12.**  That FPF brief is explicitly written for schools and districts: parents, COPPA, district procurement.  Higher-ed guides built from it then inherit its parental-consent framing, when FERPA rights transfer to the student once they enroll in postsecondary education, at any age.

None of this is obscure, but it is not where engineers usually start.  Starting in the wrong place can produce a carefully built feature for the wrong law.

## What we did, and the bill

The method applies to any system: **inventory, then classify, then map controls.**  You cannot classify what you have not listed.

**Classification is a register entry, not a property of the data.**  Engineers most often need this correction.  Someone with authority makes a determination about a *system*, and the tier that comes back sets the requirements: backup cadence, encryption, access review, retention and disposal, and a named owner.  You do not reason your way to a tier from how sensitive the data feels.

A classification determination is scoped to what the system is *for*.  The same FERPA-protected records inside a research project and inside an operational teaching platform are separate register entries with separate arguments, and an institution may reasonably put them a tier apart.  Neither classification is wrong, because the system's purpose is part of the question.

So the useful answer to "how should we protect this?" often starts with "who registered it, and at what tier?"  A tier is also a budget: it tells you which controls you are obliged to fund.  That conversation is easier before the money is spent.

This platform's guides treat coursework as high risk and write down what that requires: encryption in transit and at rest, scheduled off-box backups with tested restores, access review on a cadence, documented retention and disposal, and a named accountable owner.  The guides don't say which tier any particular institution assigned.  A reader anywhere can map those requirements onto their own register.

The platform's data inventory came from the backup plan.  The list of what stores whose data is the volume table in the operators' guide: chat databases, the usage ledger, identity, the key escrow, the search indexes, and the uploaded files.  The volume table exists because planning backups forced someone to write down every place the platform stores state.  That happens often, and it helps: the backup table becomes the data map.

The volume table also turned out to be wrong.  While building the export that gives a student their own work, we read the chat software's file schema and found that **uploaded files had never been kept.**  The chat wrote every non-image upload (agent knowledge files and attachments) inside the container itself, and no volume was mounted at that path.  Every image bump and every re-render threw the uploads away.  Nobody noticed, because file search reads the embeddings, and those were stored elsewhere and survived.  The fix was one volume per course (`3ae82a9`, 2026-09-25), and it shipped before any faculty member had uploaded a syllabus worth losing.

So the first data-protection bug this project found was data being deleted without anyone choosing to delete it.  An inventory is how you find out what your system does with data.

Treating coursework as high risk led to three protections for how course data is stored:

- **Isolation by instance instead of by permission check.**  Each course has its own chat, its own database, its own search index and, since `e5abb56`, its own document store.  The one shared component left is the database server, which asks for no credentials.  [How do you keep the courses apart?](keeping-courses-apart.md) covers the details.
- **Records with owners.**  Every request is attributed to a real person's email address, so a usage record means something and survives a roster change.
- **Egress closed by default.**  Agent actions are off unless a course record turns them on.

Treating coursework as high risk also shaped what happens to a student's records over time:

- **Custody that outlives enrollment.**  The key escrow keeps a versioned history of which key was issued to whom.  Leaving a course revokes the key and keeps the record.  [Why is there a vault?](why-a-vault.md) explains the escrow.
- **A way out for the student's own work.**  Ask the Student Guide in the {{PLATFORM}} chat to export your data from a course and you get a zip of your conversations and agents behind a link that lasts 24 hours.  It works on a closed or archived course, too.
- **An end of term that doesn't destroy anything by accident.**  Closing a course stops the spending and leaves 14 days to take work out.  Archiving revokes every key and switches off the course's sign-in.  Neither one deletes a byte.  The code says so in a comment, because a verb named "archive" is where someone would expect a delete.

The University of British Columbia made the opposite choice.  UBC built a locally hosted LLM sandbox and made it *stateless*: "For straightforward privacy and security, the Sandbox will not store user prompts or responses from the LLM" ([UBC, 2024](https://tlef.ubc.ca/uncategorized/genai-sandbox-architecture/)).  Responsibility for sensitive data went to the applications built on top: any application that stores data takes its own storage to a privacy impact assessment.

UBC designed its sandbox to avoid holding the data.  This platform holds it, because persistence is part of the teaching: students build agents and come back to them across a term, and faculty need attribution and budgets.  Every page in [your data](../your-data/index.md) describes the cost of that choice.  The two institutions faced the same privacy pressure and chose opposite architectures, and both choices are defensible.  If you build one of these systems, know which approach you chose, and why.

Harvard's AI Sandbox takes a third approach.  It publishes its ceiling: approved for data up to its Level 3 (medium-risk confidential) under its own classification scheme.  It promises interactions are not used for training, and it publishes little about retention, who can read stored conversations, or deletion.  Publish a ceiling like Harvard's: "what may I put in here?" is the most useful single line an instructor can be handed.  This platform's documentation also covers the parts Harvard leaves unpublished.  (Harvard's tiers are Harvard's, and every register differs.  The comparison is about what gets published, not about whose tier is right.)

**Self-hosting removes a class of paperwork for storage.**  The usual route for a third-party tool is a vendor contract, a data processing agreement, and a "school official with a legitimate educational interest" designation with a direct-control clause.  When the institution runs the servers, there is no third party to designate for *storage*.  Owning the stack removes that whole class of paperwork.

**Inference is still a third party** whenever the model is hosted.  A cloud model receives the prompt and the attached files under its provider's terms, whatever happens to the conversation afterward.  Self-hosting the chat moves the third-party question without retiring it: the question is now at the model endpoint, and with the agreement behind it.

The costs of treating coursework as high risk:

- **A rendering layer, a vault, and five containers per course**, to keep a boundary that a single application with careful WHERE clauses would also keep most days.
- **Operations a small team has to run**: nightly backups across two repositories with two passwords, an escrow that has to be unsealed, and a fleet to roll.
- **Every decision to store data becomes a commitment.**  A stateless service never has to answer a student who asks for everything they typed to be deleted.  This platform does.

## What is still wrong with it

The open gaps in data protection are kept up to date against the running system.  A real gap list teaches more than a finished story, and the next cohort can close these gaps.

!!! warning "Open gaps: backups, retention and deletion"
    - **Restore is not built.**  `just backup` runs two bundles off the box and keeps 7 daily, 4 weekly and 6 monthly copies.  `just restore` and the drill that proves it have not shipped, and the spec's own rule is that a backup nobody has restored from is a rumor.  So by our definition there are no backups yet.
    - **No retention policy, so no expiry.**  Ordinary conversations stay until an operator removes them.  The only thing that deletes itself is a *temporary chat*, on the chat software's shipped default of 30 days.  That default was read from the source at our pinned version and has not yet been watched expiring.
    - **No per-student deletion path.**  Nothing walks a course database and removes one person's material.
    - **The backups would outlive a deletion anyway**, for about six months, and a restore is all-or-nothing.  [Backups](../your-data/how-long-we-keep-it.md#backups) has both.

!!! warning "Open gaps: exports, archived courses, isolation and egress"
    - **The export is not everything.**  It contains a student's conversations and agents.  It does not include their usage records, their identity record, the history of keys issued to them, or their chats with the guides in the {{PLATFORM}} chat.  A request for those is handled by a person, by hand.
    - **Archiving is not deleting.**  An archived course's database is still there, and an export still reads from it.  Keeping the database is intended, and it is also data that outlives the course with no clock on it.
    - **The database server asks for no password.**  The chat software never crosses courses, but code running anywhere on the internal network could open every course's database.
    - **Inside one course, the document store is still a permission check.**  Between courses it is a container wall.
    - **Agent actions cannot be narrowed to "nowhere."**  An empty allowlist is *no* allowlist, which means the whole internet, so leaving actions off is the only complete egress answer.
    - **Whether chat logs are formally education records is with counsel.**  Meanwhile we treat them as if they are.

The three deletion gaps (no expiry, no per-student deletion path, and backups that outlive a deletion) are one problem: data you can't delete.  Removing a record from a live database is easy.  Removing it from every backup of that database is not, and a backup you can selectively edit is a backup you can no longer trust.

Mature systems solve this with **crypto-shredding**: encrypt each person's data under a key of their own, and to delete the data, destroy the key instead of hunting down the copies.  Every backup still contains the bytes, and none of them can be read.  Crypto-shredding is the only approach that makes "delete on request" true once backups exist.  It is not built here, and it is a large job: per-subject keys inside a chat database that was never designed for them, and custody for those keys that is itself backed up very carefully.

## Try it yourself

This exercise needs nothing from this platform.  Pick one system you already run, such as a lab server, a class project with a database, or a shared drive, and write down four things about it:

1. **Everything it stores.**  Include every place the system keeps state, beyond the tables you designed: logs, caches, uploads, and backups.
2. **Who each thing is about.**
3. **Which regime attaches, and what triggers it.**  Data type, contract, or your institution's register.  If you can't name the trigger, you don't know the regime yet.
4. **What you would do if someone asked for their records, or asked for them to be deleted.**  Include the copies.

Most people can't finish the first item.  This platform couldn't either: the uploads we thought we were protecting had never been kept, because nobody had listed where they were stored.

Then draft a reply to the student who asked you to delete everything they typed into the course chat this term.  If your reply says "done," check your list again.  A correct reply today says what you can give back, what you can't remove yet, and why.  That reply is harder to write than "deleted," and more useful to receive.
