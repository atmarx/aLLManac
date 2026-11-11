---
title: Privacy notice
description: What {{PLATFORM}} collects when you sign in and use it, what it is used for, who can see it, how long it is kept, and what you can ask for.
audience: student
also_reaches: [faculty]
status: proposed
owner: piper
tags: [transparency-notice, data-inventory, retention, access-control, sso, identity-broker, globus, ferpa, student-right, education-record]
regimes: [ferpa]
tethered_to:
  - apex/your-data/what-we-store.md
  - apex/your-data/who-can-see-it.md
  - apex/your-data/how-long-we-keep-it.md
  - apex/your-data/asking-about-your-data.md
  - keycloak/realm-classroom.json
  - mkdocs.yml
---

# Privacy notice

<!-- until-adopted -->
!!! warning "This is a draft that no institution has adopted yet"
    You are reading the generic text that ships with the platform.  It describes what the platform stores and who can reach it.  It is not legal text, and nobody's counsel has approved it.  This box goes away when the institution running this deployment dates its notice.

    **What is already done:**

    - The inventory of what is stored, who can see it and how long it is kept follows the platform as it ships.  Each section is a summary of a page in [Your data](your-data/index.md), which has the detail.
    - The sign-in section follows the sign-in the platform ships with, and what that sign-in is configured to ask for.
    - The parts the platform has not built are stated as not built: no retention period, no way to delete one person's data, and backups that have never been restored from.

    **What is the institution's to do before it publishes:**

    1. **Have counsel read it, and decide which laws apply.**  The notice treats course conversations as education records without concluding that they are.  Counsel decides that, and adds the rights, the offices and the contacts your laws require.
    2. **Name every outside model provider and its data terms** (`MODEL_NOTICE`).  The notice says conversations are not used for training by the platform.  It can say nothing about a provider until you do.
    3. **Set a retention period, or keep saying there is none.**  The notice is true today because it says nothing expires.
    4. **Confirm the settings the notice relies on.**  Staff see no one's conversations only while the chat software's Insights feature stays off (`ENABLE_INSIGHTS` unset).  Nothing goes to an outside service from an agent unless a course has agent actions turned on.
    5. **Check the sign-in section against your own sign-in.**  If people do not sign in through Globus, rewrite it for the provider you use.  If they do, compare it with what a real sign-in sends.
    6. **Write a separate notice for any other deployment.**  A staff or research portal keeps different things for different periods.
    7. **Say who runs it, who to ask and the date**, in the deployment's settings (`OPERATOR_NAME`, `OPERATOR_CONTACT`, `POLICY_DATE`).  Setting the date is what removes this box.
<!-- /until-adopted -->

{{PLATFORM}} is run by {{OPERATOR}}.  This notice was last changed on {{POLICY_DATE}}.

It covers {{PLATFORM}} as it is used for courses: each course's chat, and the {{PLATFORM}} chat with its guides.  A deployment set up for another purpose, such as a staff or research portal, has a notice of its own.

This page is the summary.  Each section links to the page in [Your data](your-data/index.md) that has the detail.  If the two ever disagree, tell us, because one of them is wrong.

## At a glance

- **Signing in gives us your name, your email address and your username.**  We never see your password.
- **What you type and upload is stored**, in your own course's database, and it stays until someone removes it.
- **Every request is counted against your email address**: which model, how many tokens, what it cost, and when.  The count does not include what you said.
- **Your instructor and the people who run the platform can get to your work.**  Nobody in another course can.
- **We do not use your conversations to train models, we show no advertising, and we sell nothing.**  If your course uses a model run by an outside provider, that provider's terms are its own, and the model notice under [Who can see it](#who-can-see-it) names them.
- **You can see your usage and export your work yourself.**  Deleting one person's data is not built yet.

## What we get when you sign in

You sign in through your institution's single sign-on.  Where that sign-on is reached through Globus, Globus confirms who you are and sends us a short profile: your name, your email address, your username and organization as Globus has them, and an identifier for the account you signed in with.  We keep your name, your email address, your username and that identifier.  We ask Globus for nothing else, and we never receive your password.

Globus is used here only to sign you in.  Nothing you do in {{PLATFORM}} is stored in Globus or moved over it, and we do not use Globus groups, collections or transfers.

Your account is created when an instructor adds you to a course, or the first time you sign in if no course has added you yet.  It holds your name, your email address, and which courses you are in.

More: [Who can see it](your-data/who-can-see-it.md#signing-in).

## What we keep

| What | Tied to you |
|---|---|
| Your conversations, in a course's chat and with the guides | Yes |
| The agents you build, and files you upload to a chat or an agent | Yes |
| A usage record for each request: model, tokens, cost and time | Yes, by email address |
| Your account, your roles, and the course rosters you are on | Yes |
| API keys issued to you, and the history of them | Yes |
| Problem reports you file, with the question and answer they quote | Yes |
| Backup copies of all of the above | Yes |

We do not record keystrokes, screen activity, or how long you take to answer.  The help pages set no cookies and load nothing from any outside service.  The chat sets the cookies that keep you signed in.

More: [What we store](your-data/what-we-store.md).

## What we use it for

- **To run the service**: to show you your own conversations, agents and files, and to let you share the ones you choose to share.
- **To count use and keep budgets**: each course has a budget, and each key has a limit.  The usage record is how both are kept.
- **To run a course**: your instructor and TAs see who is on the roster, who has started, and how much each person has used.
- **To fix problems**: when you file a report, the people who run the platform read it.
- **To keep the system safe and recoverable**: logs and backups.

We do not use your conversations to train or tune a model.  We do not sell what we hold, and there is no advertising.  A hosted model's provider handles what it receives under its own terms, which the model notice below names.

## Who can see it

- **You** can see everything in your own account.
- **Your instructor and TAs** see usage for their course by email address: requests, tokens, last activity and spend.  That report has counts, not what you wrote.  Assume all the same that an instructor can read what you write in their course, the way you would for anything you hand in.
- **The people who run the platform** can reach everything, because they run the servers and the backups.  Policy and professional obligation limit what they do with that access.  The software does not.
- **Nobody in another course** can see your work.  Each course has its own copy of the chat and its own database.
- **People you share with.**  An agent or a conversation is private until you share it, and you can share only inside your own course.
- **A model provider, if your course uses a hosted model.**  A model on the institution's own hardware adds no outside recipient.  A hosted one receives the prompts and files it needs to answer.  {{MODEL_NOTICE}}
- **An outside service an agent calls**, only in a course whose instructor has turned agent actions on.

More: [Who can see it](your-data/who-can-see-it.md).

## How long we keep it

**Until someone removes it.**  No retention period has been set, so ordinary conversations do not expire.  Three things do end on their own:

- **A temporary chat** deletes itself after the period the chat software sets.
- **Backups** are kept on a schedule that runs to about six months.  Something you delete today is still in the backups until the last copy holding it ages out.
- **An export link** stops working after a day.

When a course ends, its chat stays readable for 14 days so you can take your work with you, and then it is archived.  Archived is not deleted.

More: [How long we keep it](your-data/how-long-we-keep-it.md).

## What you can ask for

- **Your usage**: ask the Usage Guide in the {{PLATFORM}} chat.  It answers only for you.
- **A copy of your work**: ask the Student Guide to export your data from a course.  You get your conversations and your agents.
- **A formal records request, or a correction**: that goes to your institution's records office, not to this platform.  We treat course conversations as education records while the institution decides whether they are.
- **Deletion of your data**: there is no built way to remove one person's material from a course yet.  A request is handled by a person, by hand, and backups keep their copies until they age out.

More: [Asking about your data](your-data/asking-about-your-data.md).

## When this notice changes

The date at the top changes when the notice does, and the current notice is always at this address.

## Who to ask

{{CONTACT}}
