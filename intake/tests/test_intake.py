"""The intake's two tools and the draft's page operations (docs/staff-portal.md,
the intake room; docs/staff-portal-agents.md, "The explainer, against
stand-in tools", items 1 to 3; screens, section 1)."""

import datetime as dt
import os
import re

import pytest

from conftest import H
from svc import drafts, fields as F, timeline as T, words
from svc.server import Refused, Service


def _db(svc):
    return drafts.connect(svc.db_path)


def _draft_id(text):
    return re.search(r"/intake/d/([\w-]+)", text).group(1)


def test_an_empty_call_lists_the_fields_and_writes_nothing(svc):
    for empty in (None, {}, {"title": "", "work": "   "}):
        said = svc.draft_fields(H(), empty)
        assert "/intake/d/" not in said
    assert _db(svc).execute("SELECT count(*) FROM draft").fetchone()[0] == 0
    said = svc.draft_fields(H())
    assert said.startswith("Nothing was written.")
    # A person-only field's choices are listed, in order, and it is marked as theirs alone.
    assert "stands · Where the proposal stands (choice): the person's alone" in said
    assert "1. Not sent; 2. Under review; 3. Funded." in said
    # Choices not yet copied from the primary text are said to be missing, never guessed.
    assert "aren't loaded on this service yet" in said and "won't guess them" in said
    assert "None of them; I'm not sure, and I'd like the office to tell me" in said


def test_a_person_only_field_is_never_written(svc):
    said = svc.draft_fields(H(), {"category": "None of them", "stands": "Funded"})
    assert "Nothing was saved, and no draft was opened." in said
    assert said.count("is the person's alone to choose") == 2
    assert _db(svc).execute("SELECT count(*) FROM draft").fetchone()[0] == 0
    said = svc.draft_fields(H(), {"title": "Mutations in a model system", "stands": "Funded"})
    assert "Saved to the draft, in the words given: What the project is called (title)." in said
    assert "Not saved: Where the proposal stands (stands) is the person's alone" in said
    assert [tuple(r) for r in _db(svc).execute("SELECT field_id FROM field")] == [("title",)]


def test_what_is_saved_is_said_and_the_words_are_kept(svc):
    said = svc.draft_fields(H(), {"work": "We're asking whether a set of mutations ...", "nope": "x",
                                  "sent_on": "the 3rd"})
    assert "(work)" in said.splitlines()[0] and "Not saved: nope (nope) isn't a field" in said
    assert "give the full date as YYYY-MM-DD" in said
    v = _db(svc).execute("SELECT draft_value, value FROM field WHERE field_id='work'").fetchone()
    assert tuple(v) == ("We're asking whether a set of mutations ...",) * 2      # not tidied
    assert "https://chat.example.edu/intake/d/" in said and "Nothing is sent from the chat" in said
    # The unsent draft's own deletion date is written in words.
    assert re.search(r"deleted on its own on \d{1,2} [A-Z][a-z]+ \d{4}\.", said)


def test_the_agent_cannot_redraft_what_the_person_changed_or_confirmed(svc):
    did = _draft_id(svc.draft_fields(H(), {"title": "A", "work": "B"}))
    c, fl = _db(svc), F.load(svc.fields_path)
    by = {f["id"]: f for f in fl}
    drafts.person_set(c, did, "pi@example.edu", by["title"], "A, renamed")
    drafts.confirm(c, did, "pi@example.edu", by["work"])
    said = svc.draft_fields(H(), {"title": "A again", "work": "B again"})
    assert said.count("changed or confirmed by the person") == 2 and "Nothing was saved." in said
    # Same draft, not a second one.
    assert _draft_id(said) == did and c.execute("SELECT count(*) FROM draft").fetchone()[0] == 1


def test_the_page_states_and_what_the_office_receives(svc):
    did = _draft_id(svc.draft_fields(H(), {"title": "A", "work": "B"}))
    c, fl = _db(svc), F.load(svc.fields_path)
    by = {f["id"]: f for f in fl}
    me = "pi@example.edu"
    with pytest.raises(drafts.Gone):
        drafts.get(c, did, "someone@example.edu")          # the viewer must be the owner
    states = {r["id"]: r["state"] for r in drafts.rows(c, did, fl)}
    assert states == {"title": "drafted", "stands": "not answered", "sent_on": "not answered",
                      "work": "drafted", "category": "not answered"}
    drafts.person_set(c, did, me, by["title"], "  A  ")        # whitespace only: not a change
    drafts.person_set(c, did, me, by["work"], "B, said better")
    drafts.person_set(c, did, me, by["stands"], "Under review")
    with pytest.raises(drafts.Blocked):
        drafts.person_set(c, did, me, by["category"], "Something invented")
    with pytest.raises(drafts.Blocked, match="Not confirmed yet"):
        drafts.submit(c, did, me, fl, asserted=True)
    for f in ("title", "work", "stands"):
        drafts.confirm(c, did, me, by[f])
    with pytest.raises(drafts.Blocked, match="assertion"):
        drafts.submit(c, did, me, fl, asserted=False)
    ref = drafts.submit(c, did, me, fl, asserted=True)
    assert ref.startswith("IN-")
    sent = {s["id"]: s for s in drafts.submission(c, did, fl)}
    assert (sent["title"]["changed"], sent["work"]["changed"], sent["stands"]["changed"]) == (False, True, False)
    assert sent["sent_on"] == {"id": "sent_on", "label": "When it went out", "value": None, "answered": False,
                               "confirmed_at": None, "changed": False}
    assert set(sent["work"]) == {"id", "label", "value", "answered", "confirmed_at", "changed"}   # no draft text
    with pytest.raises(drafts.Blocked, match="has been sent"):
        drafts.person_set(c, did, me, by["title"], "late")
    # A write after sending opens a new draft; the sent one is untouched.
    assert _draft_id(svc.draft_fields(H(), {"title": "Next"})) != did


def test_an_editing_clears_confirmation_and_put_back_restores_the_draft(svc):
    did = _draft_id(svc.draft_fields(H(), {"title": "A"}))
    c, by = _db(svc), {f["id"]: f for f in F.load(svc.fields_path)}
    drafts.confirm(c, did, "pi@example.edu", by["title"])
    drafts.person_set(c, did, "pi@example.edu", by["title"], "Z")
    r = c.execute("SELECT value, confirmed_at, changed FROM field").fetchone()
    assert tuple(r) == ("Z", None, 1)
    drafts.put_draft_back(c, did, "pi@example.edu", by["title"])
    assert tuple(c.execute("SELECT value, confirmed_at, changed FROM field").fetchone()) == ("A", None, 0)


def test_delete_and_expiry_are_the_same_answer(svc):
    c = _db(svc)
    did = _draft_id(svc.draft_fields(H(), {"title": "A"}))
    drafts.delete(c, did, "pi@example.edu")
    with pytest.raises(drafts.Gone):
        drafts.get(c, did, "pi@example.edu")
    did = _draft_id(svc.draft_fields(H(), {"title": "B"}))
    c.execute("UPDATE draft SET expires_at='2000-01-01T00:00:00+00:00'")
    with pytest.raises(drafts.Gone):
        drafts.get(c, did, "pi@example.edu")
    assert c.execute("SELECT count(*) FROM field").fetchone()[0] == 0          # gone with it


def test_who_is_asking_comes_from_the_chat_and_nothing_else(svc):
    with pytest.raises(Refused, match="didn't recognise the chat"):
        svc.draft_fields(H(token="wrong"))
    with pytest.raises(Refused, match="can't tell who is asking"):
        svc.timeline({"authorization": "Bearer tok-intake", "x-user-email": "{{LIBRECHAT_USER_EMAIL}}"})
    with pytest.raises(ValueError, match="INTAKE_MCP_TOKEN"):
        Service(svc.db_path, svc.fields_path, svc.obligations_path, "", 7, "")


def test_the_timeline_says_what_today_is_and_writes_dates_in_words(svc):
    today = words.today("UTC")
    said = svc.timeline(H())
    assert said.startswith(f"Today is {words.weekday(today)}.")
    assert not re.search(r"\d{4}-\d{2}-\d{2}", said)                 # no ISO date anywhere, notes included
    assert "17 November 2026 counting from issuance, or 25 November 2026 counting from release" in said
    assert "None published as of 27 October 2026." in said
    assert "Scheduled: no date has been set." in said
    loose = svc.timeline(H(), "the 17th of next month")
    assert loose.startswith(f"Today is {words.weekday(today)}.") and "isn't a full date" in loose


def test_scheduled_is_kept_apart_from_what_happened_and_a_stale_row_says_so():
    import yaml
    from conftest import OBLIGATIONS
    t = {"rows": yaml.safe_load(OBLIGATIONS), "review_by": dt.date(2026, 11, 24)}
    before = T.answer(t, dt.date(2026, 11, 20), dt.date(2026, 11, 1))
    assert "Today is Sunday, 1 November 2026." in before and "You asked about Friday, 20 November 2026." in before
    assert "On 20 November 2026: one count's date has passed and the other's has not." in before
    assert "At the last check, on 27 October 2026: pending." in before
    assert "It is due for review by 24 November 2026." in before
    after = T.answer(t, None, dt.date(2026, 12, 1))
    assert "the table is behind on this row" in after and "past its review date, 24 November 2026" in after
    assert "1 row passed its date after the last check." in after
    assert "On 1 December 2026: both counts' dates have passed." in after


@pytest.mark.skipif(not os.path.exists(os.path.expanduser("~/Code/research-compliance-kb/intake-fields.yaml")),
                    reason="research compliance's own files aren't on this machine")
def test_research_compliances_own_files_load():
    kb = os.path.expanduser("~/Code/research-compliance-kb")
    fl = F.load(f"{kb}/intake-fields.yaml")
    assert len(fl) == 13 and {f["id"] for f in fl if f["person_only"]} == {"proposal_status", "category"}
    said = T.answer(T.load(f"{kb}/dated-obligations.yaml"), None, dt.date(2026, 11, 11))
    assert not re.search(r"\d{4}-\d{2}-\d{2}", said) and "Today is Wednesday, 11 November 2026." in said
