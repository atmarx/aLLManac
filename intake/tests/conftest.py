import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

FIELDS = """
- id: title
  label: What the project is called
  asks: The working title.
  kind: text
  person_only: false
- id: stands
  label: Where the proposal stands
  asks: Asked plainly.
  kind: choice
  person_only: true
  options: [Not sent, Under review, Funded]
- id: sent_on
  label: When it went out
  asks: A date if you have one.
  kind: date
  person_only: false
- id: work
  label: What the work is
  asks: In your words.
  kind: long
  person_only: false
- id: category
  label: Which category applies
  asks: Yours to state.
  kind: choice
  person_only: true
  options_from: the rule's own names, copied from the primary text.
  options_always_last: [None of them, "I'm not sure, and I'd like the office to tell me"]
"""

OBLIGATIONS = """# A neutral table for the tests.
#   checked_on: 2026-10-27
#   review_by:  2026-11-24
- id: O1
  obligation: Guidance is issued.
  who: agencies
  clock: "120 days"
  date_from_issuance: 2026-11-17
  date_from_release: 2026-11-25
  status: pending
  status_note: None published as of 2026-10-27.
  source: "The policy"
  as_of: 2026-10-27
- id: O2
  obligation: A review body is set up.
  who: the government
  date_from_issuance: 2026-10-18
  date_from_release: null
  status: published
  as_of: 2026-10-27
- id: O3
  obligation: A draft takes effect.
  date_from_issuance: null
  date_from_release: null
  status: pending
  as_of: 2026-10-27
"""

TOKEN = "tok-intake"


def H(email="pi@example.edu", token=TOKEN):
    return {"authorization": f"Bearer {token}", "x-user-email": email}


@pytest.fixture
def svc(tmp_path):
    from svc.server import Service
    (tmp_path / "fields.yaml").write_text(FIELDS)
    (tmp_path / "obligations.yaml").write_text(OBLIGATIONS)
    return Service(str(tmp_path / "intake.sqlite"), str(tmp_path / "fields.yaml"),
                   str(tmp_path / "obligations.yaml"), "https://chat.example.edu", 7, TOKEN, "UTC")
