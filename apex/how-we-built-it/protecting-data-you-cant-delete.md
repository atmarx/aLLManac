---
title: How do you protect data you can't delete?
description: Course data carries obligations that outlast the term. Which regime attaches to which data, how classification drives controls, and why running it yourself changes the problem.
audience: builder
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [ferpa, gdpr, nist-800-53, nist-800-171, cui, fisma, data-classification, high-risk-data, education-record, retention, secure-deletion, backup, data-processing-agreement, azure, aws, kubernetes, faculty-duty]
regimes: [ferpa, gdpr, nist-800-53, nist-800-171]
tethered_to:
  - justfile
  - docs/admin-guide.md#backups
  - registrar/reconcile.py
---

# How do you protect data you can't delete?

<!-- SCAFFOLD.  The literacy piece.  Carries the corrections that make the
     whole data-protection thread worth teaching.

     COUNSEL BOUNDARY: describes regimes in general terms and describes our
     system factually.  Makes no compliance claim about this platform and
     gives no legal advice.  @nora reviews before status: published. -->

## 1. The question

<!-- Open concrete rather than abstract.  A course generates conversations,
     uploaded files, and usage records tied to named students.  The term
     ends.  The records do not.  Who is allowed to read them, how long do
     they stay, and what happens when someone asks for them back? -->

## 2. The obvious answer, taken seriously

<!-- "Encrypt everything, lock it down, delete it when they ask."

     Steelman it — those are good instincts and roughly the right shape.
     Then show why each one is more specific than it sounds:
     - encrypt *what*, against *which* threat, and who holds the key
     - lock it down *from whom*, given the operator runs the servers
     - delete it *when* — and, as beat 3 gets into, on whose authority -->

## 3. What broke — the assumption, not the system

<!-- The two corrections that carry this page.

     **FERPA is not an erasure regime.**  It grants inspection and review,
     the right to request amendment, consent before disclosure of PII (with
     exceptions), and the right to complain to the Department of Education.
     There is no delete-my-data right in it.  Engineers arrive expecting one
     because GDPR Article 17 and CCPA trained the instinct on consumer
     products.  Building a deletion pipeline to satisfy FERPA is solving a
     requirement that FERPA never stated, while possibly missing the ones it
     did.

     **NIST 800-53 and 800-171 are not triggered by FERPA.**  800-53 is the
     control catalog for federal information systems under FISMA.  800-171
     covers CUI in nonfederal systems and arrives through *contract* —
     DFARS flow-down and similar — which is why colleagues in sponsored
     research meet it and a teaching platform may not.  Neither attaches
     because student data is sensitive.

     What actually governs course data: FERPA, state student-privacy
     statutes, and — the one that binds day to day — the institution's own
     data classification policy.

     Land the transferable rule: **the trigger is usually data type plus
     contract, not a general duty to be secure.**  Engineers who learn to ask
     "what makes this regime apply to me?" stop applying the wrong one. -->

## 4. What we did, and the bill

<!-- The method, which is the actually transferable skill:

     **Inventory, then classify, then map controls.**  You cannot classify
     what you have not enumerated.

     The correction that belongs here, because engineers get it wrong and it
     is the most transferable thing on the page: **classification is a
     register entry, not a property of the data.**  Someone with authority
     makes a determination about a *system*, and the tier that comes back
     carries the actual requirements — backup cadence, encryption, access
     review.  You do not reason your way to a tier from how sensitive the
     data feels.

     And the determination is scoped.  The same data type lands in different
     tiers depending on what the system is for: FERPA-protected data inside a
     research project registers high here, while an operational teaching
     platform holding the same category of record is a separate entry with a
     separate argument, plausibly a tier lower.  Neither is wrong.  The tier
     encodes what handling makes sense in that context, and context is part
     of the question.

     Two consequences worth teaching: the honest engineering answer to "how
     should we protect this?" often starts with "who registered it and at
     what tier," and a tier is a **budget** as much as a burden — it tells
     you which controls you are obliged to fund.  Our inventory is the volume map — chat
     databases, the ledger, identity, escrow, derived indexes — and it exists
     because backups forced us to write it down.  Point that out: the backup
     table became the data map, which is a common and useful accident.

     Then what the classification bought, concretely:
     - isolation by instance rather than by permission check
     - attribution keyed to a real identity, so records have owners
     - egress default-closed (agent actions off unless enabled)
     - escrow custody history that survives un-enrollment

     **The bill** — the honest one:
     - a rendering layer, a vault, and per-course containers, all to hold a
       line that a single app with good WHERE clauses would also hold most
       days
     - operational surface that a small team has to actually operate

     **The self-hosting dividend**, which is the part nobody writes down:
     the usual pattern for a third-party tool is a vendor contract, a data
     processing agreement, and a "school official with legitimate
     educational interest" designation with a direct-control clause.  When
     the institution runs the servers, there is no third party to designate
     and the data never leaves institutional control.  Owning the stack
     removes an entire class of compliance work.  Say it plainly — it is a
     real and under-told advantage. -->

## 5. What is still wrong with it

<!-- TETHERED, and this is the section with the most to say.  Current state:

     !!! warning "Open gaps"
         - `just backup` is designed, not implemented — no schedule, no
           off-box copy, no tested restore
         - no automated retention or expiry
         - no per-student deletion path
         - no domain allowlist on agent actions, so an enabled course can
           send content anywhere
         - whether chat logs are formally education records is with counsel

     Say why the list is published rather than fixed first: a reader learns
     more from a real gap list than from a finished story, and the gaps are
     what the next cohort gets to close. -->

## 5b. What everyone else did — banked prior art

<!-- Researched 2026-07-31.  Sources verified; use them, do not re-derive.

     **UBC's LLM Sandbox — the contrast case that teaches the most.**
     UBC built a locally-hosted LLM service and made it deliberately
     STATELESS: "the infrastructure that constitutes the LLM Sandbox does
     not need to store any data whatsoever.  It is essentially idempotent."
     They chose that specifically to simplify their Privacy Impact
     Assessment, and pushed responsibility for sensitive data onto the
     applications built on top.  Data residency (keeping data in Canada)
     drove the self-hosting decision.  Runs Ollama on AWS EC2.

     This is beat-4 gold.  They engineered AROUND the data problem.  We took
     it on, because persistence IS the pedagogy here — students build agents
     and come back to them, faculty need attribution and budgets.  Every
     page in your-data/ is the bill for that choice.  Two institutions, same
     privacy pressure, opposite architectures, and both defensible.  Say
     which one we are and why.

     **Harvard's AI Sandbox — publishes a ceiling, and little else.**
     States it is approved for data up to Level 3 (Medium Risk
     Confidential) under Harvard's classification scheme, promises data is
     not used to train LLMs, and gates access behind a training module.
     Publishes nothing about retention, who can access stored interactions,
     or deletion.

     Two things follow.  One: publishing an explicit classification ceiling
     is a concrete practice worth copying, and it is the single most useful
     line an instructor can be handed.  Two: the gap this section exists to
     fill is unfilled at the most-cited peer implementation, so our
     your-data/ pages are ahead rather than catching up.  Do not overclaim
     the comparison — Harvard's tiers are Harvard's, not Drexel's.

     **"There is no such thing as a 'FERPA seal of approval.'"**
     Michael Hawes, then director of the US Department of Education's
     Student Privacy Policy and Assistance Division, quoted in FPF's
     *Vetting Generative AI Tools for Use in Schools* (April 2024).  FERPA
     binds funded schools, not companies, so no product can be
     FERPA-compliant — the question is whether an institution can use it in
     a compliant manner.  An entire vendor category sells the thing that
     cannot exist; a web search for FERPA-compliant AI returns mostly that.

     **Most available guidance is K-12-shaped, and higher ed imports its
     errors.**  FPF's brief is explicitly K-12 (parents, COPPA, districts).
     Higher-ed faculty guides then inherit parental-consent framing, when
     FERPA rights transfer to the student on postsecondary enrollment at any
     age.  Naming this is a real service to the reader.

     **The awareness gap, which justifies the whole approach.**  EDUCAUSE
     (Jan 2026): 94% of higher-ed workers used AI tools for work in the past
     six months; 54% know their institution's AI policy.  Their 2024
     landscape study: 80% use, fewer than one in four aware of a formal
     policy.  Writing more policy does not reach people who do not read
     policy — which is why the faculty duties here are taught through pages
     addressed to students.

     **Also useful:** FPF's lifecycle spine (notice → consent → collection →
     use → sharing → deletion); 128+ state student privacy laws, many of
     which DO impose retention and deletion duties that FERPA does not; and
     FPF's high-risk-decision-making section, which is the frame for
     AI-assisted grading. -->

## 6. How this looks on other stacks

<!-- - **Azure** — Purview for classification and lineage, Policy for
       enforcement, Key Vault for key custody, immutable Blob storage with
       legal hold for retention you must be able to prove.
     - **AWS** — Macie for discovery and classification, S3 Object Lock for
       WORM retention, KMS with per-tenant keys, CloudTrail as the audit
       record.
     - **Kubernetes** — the honest note is that k8s gives you almost none of
       this natively.  etcd encryption at rest is a flag, audit logging is a
       policy file you must write, and retention lives in whatever storage
       backs your PVCs.  Compliance on k8s is assembled, not enabled.

     The invariant: **crypto-shredding** — encrypt per subject and destroy
     the key — is how mature systems answer deletion when the data is spread
     across backups you cannot selectively edit.  Worth naming, because it is
     the technique that makes "delete on request" tractable at all once
     backups exist. -->

## 7. Try it yourself

<!-- An exercise rather than a click-through, since this page is conceptual:
     classify one system you already run.  List what it stores, who it is
     about, what regime attaches and why, and what would happen if someone
     asked for their records.  Most readers discover they cannot answer the
     first question, which is the lesson. -->
