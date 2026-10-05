---
title: How do you protect data you can't delete?
description: Course data comes with obligations that outlast the term.  Which regime attaches to which data, why classification is a decision someone registers and not a feeling about the data, and what running it yourself changes.
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

It is a reasonable thing to ask.  It is also three questions wearing one sentence: whether anybody is obliged to do it, whether anybody is allowed to, and whether the system can.  The third is the easiest, and it is the one engineers start with.

## The question

A course on this platform produces three kinds of record about named people: the conversations, both sides of them; the files students and instructors uploaded; and the usage records — which model, how many tokens, when, against whose key.  The term ends.  The records do not.

So: who is allowed to read them, how long do they stay, and what happens when someone asks for them back, or asks for them gone?

[How long we keep it](../your-data/how-long-we-keep-it.md) and [Asking about your data](../your-data/asking-about-your-data.md) answer that from the student's chair, including the gap list.  Here is the builder's version — how the answers got decided, and what deciding them cost.

## The obvious answer, taken seriously

*Encrypt everything, lock it down, delete it when they ask.*

Those are good instincts, and a team that does all three is ahead of most.  Each is more specific than it sounds, and the specifics are where the work is.

- **Encrypt what, against which threat, and who holds the key?**  Disk encryption protects a drive that walks out of the building.  It does nothing about the operator, who runs the machine with the drive unlocked, or about a backup copied somewhere with its key beside it.
- **Lock it down from whom?**  The people with the most access to course data are the people running the servers.  "Locked down" has to say something about them, or it says very little.
- **Delete it when — and on whose authority?**  That one looks like an engineering task, and the next section is about why it is a legal question first.

## What broke — the assumption, not the system

The system did not break here.  The assumption did, and it is the same assumption almost everyone arrives with.

**FERPA is not an erasure regime.**  It gives students the rights to inspect, amend, consent to disclosure and complain ([the full list](../your-data/asking-about-your-data.md#what-ferpa-gives-you)), and no delete-my-data right.  Engineers expect one: GDPR's Article 17 and the state consumer privacy laws trained the instinct on consumer products.  A team that builds a deletion pipeline "for FERPA" is satisfying a requirement FERPA never stated, and quite possibly missing the ones it did.

The federal security frameworks are not triggered by student data either.  NIST SP 800-53 is the control catalog for federal information systems under FISMA.  NIST SP 800-171 covers Controlled Unclassified Information in nonfederal systems, and it arrives by *contract* — a DFARS clause, or similar language flowed down from a federal sponsor.  So colleagues in sponsored research meet it and a teaching platform usually does not.  Neither one attaches because student data is sensitive.

What governs course data is less famous and more local: FERPA, the state student-privacy statutes (well over a hundred of them, and many *do* impose retention and deletion duties FERPA does not), and — the one that binds day to day — the institution's own data classification policy.

**The transferable rule: the trigger is usually data type plus contract, not a general duty to be secure.**  An engineer who learns to ask *"what makes this regime apply to me?"* stops applying the wrong one.

The wrong answer is also easy to find:

- **"There is no such thing as a 'FERPA seal of approval.'"**  That is Michael Hawes, a former director of the Department of Education's Student Privacy Policy and Assistance Division, as quoted in the Future of Privacy Forum's [*Vetting Generative AI Tools for Use in Schools*](https://fpf.org/wp-content/uploads/2024/10/Ed_AI_legal_compliance.pdf_FInal_OCT24.pdf) (April 2024).  FERPA binds the institutions that receive federal funding and reaches the companies that sell to them only through those institutions, so no product can *be* FERPA-compliant.  The real question is whether an institution can use it in a compliant way.  Search for "FERPA-compliant AI" anyway and most of what comes back is selling the thing that cannot exist.
- **Most of the available guidance is shaped for K-12.**  That FPF brief is explicitly written for schools and districts — parents, COPPA, district procurement.  Higher-ed guides built from it then inherit its parental-consent framing, when FERPA rights transfer to the student once they enroll in postsecondary education, at any age.

None of this is obscure.  It is not where an engineer starts, and the cost of starting in the wrong place is a carefully built feature for the wrong law.

## What we did, and the bill

The method is the transferable part, and it fits on one line: **inventory, then classify, then map controls.**  You cannot classify what you have not listed.

**Classification is a register entry, not a property of the data.**  This is the correction engineers most often need.  Someone with authority makes a determination about a *system*, and the tier that comes back sets the requirements — backup cadence, encryption, access review, retention and disposal, a named owner.  You do not reason your way to a tier from how sensitive the data feels.

And the determination is scoped to what the system is *for*.  The same FERPA-protected records inside a research project and inside an operational teaching platform are separate entries with separate arguments, and an institution may reasonably put them a tier apart.  Neither is wrong.  Context is part of the question.

So the useful answer to "how should we protect this?" often starts with "who registered it, and at what tier?"  And a tier is a budget as much as a burden: it tells you which controls you are obliged to fund, and that is an easier conversation before the money is spent.

These guides treat coursework as high risk and write down what that requires — encryption in transit and at rest, scheduled off-box backups with tested restores, access review on a cadence, documented retention and disposal, and a named accountable owner.  They don't say which tier any particular institution assigned.  A reader anywhere can map that onto their own register.

The inventory came from the backups.  Our list of what stores whose data is the volume table in the operators' guide — chat databases, the usage ledger, identity, the key escrow, the search indexes, the uploaded files — and it exists because a backup plan forced someone to write down every place state lives.  That is a common and useful accident: the backup table becomes the data map.

It also showed that the map was wrong.  While building the export that hands a student their own work, we read the chat software's file schema and found that **uploaded files had never been kept.**  The chat wrote every non-image upload — agent knowledge files, attachments — inside the container itself, and nothing mounted that path.  Every image bump and every re-render threw them away.  Nobody noticed, because file search reads the embeddings, and those were stored elsewhere and survived.  The fix was one volume per course (`3ae82a9`, 2026-09-25), and it shipped before any faculty had uploaded a syllabus worth losing.

The first data-protection bug we found, in a project about data you cannot delete, was data being deleted that nobody had chosen to delete.  An inventory is how you find out what your system is doing.

What treating it as high risk bought:

- **Isolation by instance instead of by permission check.**  Each course has its own chat, its own database, its own search index and, since `e5abb56`, its own document store.  The one shared room left is the database server, which asks for no credentials — [How do you keep the courses apart?](keeping-courses-apart.md) tells that story.
- **Records with owners.**  Every request is attributed to a real person's email address, so a usage record means something and survives a roster change.
- **Egress closed by default.**  Agent actions are off unless a course record turns them on.
- **Custody that outlives enrollment.**  The key escrow keeps a versioned history of which key was issued to whom.  Leaving a course revokes the key and keeps the record — see [Why is there a vault?](why-a-vault.md).
- **A way out for the student's own work.**  Ask the Student Guide in the {{PLATFORM}} chat to export your data from a course and you get a zip of your conversations and agents behind a link that lasts 24 hours.  It works on a closed or archived course, too.
- **An end of term that doesn't destroy anything by accident.**  Closing a course stops the spending and leaves 14 days to take work out.  Archiving revokes every key and switches off the course's sign-in.  Neither one deletes a byte, and the code says so in a comment, because a verb named "archive" is exactly where someone would expect a delete.

The contrast case teaches more than any of those.  The University of British Columbia built a locally hosted LLM sandbox and made it *stateless* by design: "For straightforward privacy and security, the Sandbox will not store user prompts or responses from the LLM" ([UBC, 2024](https://tlef.ubc.ca/uncategorized/genai-sandbox-architecture/)).  Responsibility for sensitive data went to the applications built on top — any application that holds data takes its own storage to a privacy impact assessment.

They engineered around the data problem.  We took it on.  Here persistence *is* the teaching: students build agents and come back to them across a term, and faculty need attribution and budgets.  Every page in [your data](../your-data/index.md) is the bill for that choice.  Two institutions, the same privacy pressure, opposite architectures, and both defensible.  Know which one you are, and why.

Harvard's AI Sandbox sits somewhere else again.  It publishes the ceiling — approved for data up to its Level 3 (medium-risk confidential) under its own classification scheme — and promises interactions are not used for training, and it publishes little about retention, who can read stored conversations, or deletion.  Copy the ceiling: "what may I put in here?" is the most useful single line an instructor can be handed.  The silence after it is the gap our documentation fills.  (Harvard's tiers are Harvard's, and every register differs.  The comparison is about what gets published, not about whose tier is right.)

**The self-hosting dividend**, the part that rarely gets written down.  The usual route for a third-party tool is a vendor contract, a data processing agreement, and a "school official with a legitimate educational interest" designation with a direct-control clause.  When the institution runs the servers, there is no third party to designate for *storage*.  Owning the stack removes a whole class of paperwork.

**But inference is still a third party** whenever the model is hosted.  A cloud model receives the prompt and the attached files under its provider's terms, whatever happens to the conversation afterward.  Self-hosting the chat moves the question without retiring it: it is now at the model endpoint, and with the agreement behind it.

The bill:

- **A rendering layer, a vault, and five containers per course**, to keep a line that a single application with careful WHERE clauses would also keep most days.
- **Operations a small team has to run** — nightly backups across two repositories with two passwords, an escrow that has to be unsealed, a fleet to roll.
- **Every persistence decision becomes a promise.**  A stateless service never has to answer the email at the top.  We do.

## What is still wrong with it

This section is maintained against the running system.  A real gap list teaches more than a finished story, and the gaps are what the next cohort gets to close.

!!! warning "Open gaps"
    - **Restore is not built.**  `just backup` runs two bundles off the box and keeps 7 daily, 4 weekly and 6 monthly copies.  `just restore` and the drill that proves it have not shipped, and the spec's own rule is that a backup nobody has restored from is a rumor.  So by our definition there are no backups yet.
    - **No retention policy, so no expiry.**  Ordinary conversations stay until an operator removes them.  The only thing that deletes itself is a *temporary chat*, on the chat software's shipped default of 30 days — read from the source at our pinned version, not yet watched expiring.
    - **No per-student deletion path.**  Nothing walks a course database and removes one person's material.
    - **The backups would outlive a deletion anyway** — for about six months, and a restore is all-or-nothing.  [Backups](../your-data/how-long-we-keep-it.md#backups) has both.
    - **The export is not everything.**  It contains a student's conversations and agents.  It does not include their usage records, their identity record, the history of keys issued to them, or their chats with the guides in the {{PLATFORM}} chat.  A request for those is handled by a person, by hand.
    - **Archiving is not deleting.**  An archived course's database is still there, and an export still reads from it.  That is intended, and it is also data that outlives the course with no clock on it.
    - **The database server asks for no password.**  The chat software never crosses courses, but code running anywhere on the internal network could open every course's database.
    - **Inside one course, the document store is still a permission check.**  Between courses it is a container wall.
    - **Agent actions cannot be narrowed to "nowhere."**  An empty allowlist is *no* allowlist — the whole internet — so leaving actions off is the only complete egress answer.
    - **Whether chat logs are formally education records is with counsel.**  Meanwhile we treat them as if they are.

The deletion gaps are one problem seen from three sides, and it is the problem in the title.  Removing a record from a live database is easy.  Removing it from every archive of that database is not, and an archive you can selectively edit is an archive you can no longer trust.

The technique mature systems use is **crypto-shredding**: encrypt each person's data under a key of their own, and to delete it, destroy the key instead of hunting down the copies.  Every backup still contains the bytes, and none of them can be read.  It is the only approach that makes "delete on request" true once backups exist.  It is not built here, and it is not small — it means per-subject keys inside a chat database that was never designed for them, and custody for those keys that is itself backed up very carefully.  But it is the shape of the answer.  Learn the name before you need it.

## Try it yourself

The exercise is conceptual and needs nothing from this platform.  Pick one system you already run — a lab server, a class project with a database, a shared drive — and write down four things:

1. **Everything it stores.**  Not the tables you designed.  Every place state lives, including logs, caches, uploads, and backups.
2. **Who each thing is about.**
3. **Which regime attaches, and what triggers it.**  Data type, contract, or your institution's register.  If you can't name the trigger, you don't know the regime yet.
4. **What you would do if someone asked for their records — or asked for them gone.**  Including the copies.

Most people can't finish the first item.  We learned the same lesson the expensive way: the uploads we were protecting didn't exist, because nobody had listed where they lived.

Then reread the email at the top and draft the reply.  If it says "done," check your list again.  A correct one today says what you can give back, what you can't remove yet, and why — and that is a harder sentence to write than "deleted," and a more useful one to receive.
