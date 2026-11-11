"""The intake room's tool server: two tools for the explainer agent.

  * draft_fields: draft the fields of a submission from what the person
    said, and hand back the link to the page where they review, confirm and
    send it.  An empty call lists the fields and writes nothing.
  * timeline: the dated table of obligations, with what today is.

It is on the platform's track (@xram, 11-11): the chat stamps who is asking
(X-User-Email) and presents this service's token, the way usage-mcp works,
and only this platform's chat calls it.  Identity is never an argument.

Configuration, all from the environment:
  INTAKE_MCP_TOKEN    the token the chat presents (required)
  INTAKE_DB           the drafts' SQLite file
  INTAKE_FIELDS       research compliance's field list (outside this repo)
  INTAKE_OBLIGATIONS  research compliance's dated table (outside this repo)
  INTAKE_LINK_BASE    where the review page is served, e.g. https://<chat host>
  INTAKE_DRAFT_DAYS   days an unsent draft lives before it is deleted (required:
                      the office's number, so no default is guessed here)
  INTAKE_TZ           the office's time zone, for "today" (IANA; UTC unset)
"""

import datetime as dt
import hmac
import os
from contextlib import closing

from . import drafts, fields as F, timeline as T, words


class Refused(Exception):
    pass


class Service:
    def __init__(self, db_path: str, fields_path: str, obligations_path: str, link_base: str, days: int,
                 token: str, tz: str | None = None):
        if not token:
            raise ValueError("INTAKE_MCP_TOKEN is unset; the service refuses to start without one")
        if days < 1:
            raise ValueError("INTAKE_DRAFT_DAYS must be a whole number of days, 1 or more")
        self.db_path, self.fields_path, self.obligations_path = db_path, fields_path, obligations_path
        self.link_base, self.days, self.token, self.tz = link_base.rstrip("/"), days, token, tz
        F.load(fields_path)                     # fail at start, not on a person's first call
        T.load(obligations_path)

    @classmethod
    def from_env(cls) -> "Service":
        days = os.environ.get("INTAKE_DRAFT_DAYS", "")
        if not days.isdigit():
            raise ValueError("INTAKE_DRAFT_DAYS is unset: how long an unsent draft lives is the office's to set")
        return cls(os.environ.get("INTAKE_DB", "/data/intake.sqlite"), os.environ["INTAKE_FIELDS"],
                   os.environ["INTAKE_OBLIGATIONS"], os.environ.get("INTAKE_LINK_BASE", ""), int(days),
                   os.environ.get("INTAKE_MCP_TOKEN", ""), os.environ.get("INTAKE_TZ"))

    def who(self, headers: dict) -> str:
        """The asker's email, from the headers the chat stamps, or Refused."""
        h = {k.lower(): v for k, v in (headers or {}).items()}
        got = h.get("authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(got.encode(), self.token.encode()):
            raise Refused("This tool service didn't recognise the chat calling it, so it did nothing.  "
                          "The people who run this service can fix that; nothing you did caused it.")
        email = h.get("x-user-email", "").strip().lower()
        if not email or email.startswith("{{"):
            raise Refused("This tool can't tell who is asking, so it did nothing.  Sign in again and retry.")
        return email

    def link(self, draft_id: str) -> str:
        return f"{self.link_base}/intake/d/{draft_id}"

    def _expires(self, d) -> str:
        return words.day(dt.datetime.fromisoformat(d["expires_at"]).date())

    def draft_fields(self, headers: dict, fields: dict | None = None) -> str:
        who = self.who(headers)
        listed = F.load(self.fields_path)
        with closing(drafts.connect(self.db_path)) as c:
            if not fields:
                return self._list(c, who, listed)
            r = drafts.agent_write(c, who, listed, fields, self.days)
        label = {f["id"]: f["label"] for f in listed}
        out = []
        if r["saved"]:
            out.append("Saved to the draft, in the words given: "
                       + "; ".join(f"{label[x]} ({x})" for x in r["saved"]) + ".")
        else:
            out.append("Nothing was saved" + (", and no draft was opened." if r["draft"] is None else "."))
        for fid, why in r["refused"]:
            out.append(f"Not saved: {label.get(fid, fid)} ({fid}) {why}.")
        if r["draft"] is not None:
            out.append(f"The draft: {self.link(r['draft']['id'])}")
            out.append("Nothing is sent from the chat.  The person reviews every field on that page, confirms "
                       "each one, and sends it themselves.  Unsent, it is deleted on its own on "
                       f"{self._expires(r['draft'])}.")
        return "\n".join(out)

    def _list(self, c, who: str, listed: list[dict]) -> str:
        out = ["Nothing was written.  These are the fields of a submission, in order.  A draft opens only when "
               "this tool is given at least one field's text.", ""]
        for f in listed:
            head = f"- {f['id']} · {f['label']} ({f['kind']})"
            if not f["person_only"]:
                out.append(f"{head}: {f['asks']}")
                continue
            out.append(f"{head}: the person's alone.  This tool will not write it, and no value is suggested "
                       f"for it.  {f['asks']}")
            if f["options"]:
                out.append("  Its choices, in the order the page shows them: "
                           + "; ".join(f"{i}. {o}" for i, o in enumerate(F.choices(f), 1)) + ".")
            elif f["options_from"]:
                out.append("  Its main choices aren't loaded on this service yet.  They are to be copied from "
                           "the primary text, and this tool won't guess them."
                           + ("  The page always ends with: " + "; ".join(f["always_last"]) + "."
                              if f["always_last"] else ""))
        d = drafts.open_draft(c, who)
        if d is not None:
            out += ["", f"The person already has a draft open: {self.link(d['id'])}  Unsent, it is deleted on "
                        f"its own on {self._expires(d)}."]
        return "\n".join(out)

    def timeline(self, headers: dict, date: str = "") -> str:
        self.who(headers)
        today = words.today(self.tz)
        asked = None
        if (date or "").strip():
            asked = words.parse(date)
            if asked is None:
                return (f"Today is {words.weekday(today)}.  {date!r} isn't a full date.  Give it as "
                        "YYYY-MM-DD, worked out from today, and say it back to the person in words.")
        return T.answer(T.load(self.obligations_path), asked, today)


def build_mcp(svc: Service):
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError
    from fastmcp.server.dependencies import get_http_headers

    mcp = FastMCP("intake", mask_error_details=True)

    def run(fn, *a):
        try:
            # include= because get_http_headers strips authorization by default.
            return fn(get_http_headers(include={"authorization"}), *a)
        except Refused as e:
            raise ToolError(str(e))

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
    def draft_fields(fields: dict[str, str] | None = None) -> str:
        """Draft the fields of a submission to the office from what the
        person has said, in their words, and get the link to the page where
        they review, confirm and send it.  `fields` maps a field's id to its
        text.  Called with nothing, it lists the fields, including the
        choices of the ones only the person may fill, and writes nothing.
        It never writes a field only the person may fill, or one they have
        already changed or confirmed on the page.  Say a field was recorded
        only if this tool's answer names it as saved.  Nothing is sent from
        the chat: only the person sends, on the page."""
        return run(svc.draft_fields, fields)

    @mcp.tool(annotations={"readOnlyHint": True})
    def timeline(date: str = "") -> str:
        """The dated table of obligations: each one's scheduled dates, its
        status at the last check, and how old that check is.  It always
        says what today is.  `date` is a full date, YYYY-MM-DD; for a loose
        one ("the 17th of next month"), call with no date first, work the
        date out from the today it gives, and say it back to the person.
        Show the dates as this tool writes them."""
        return run(svc.timeline, date)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request):
        from starlette.responses import JSONResponse
        return JSONResponse({"status": "ok"})

    return mcp


def main():
    svc = Service.from_env()
    build_mcp(svc).run(transport="http", host="0.0.0.0", port=8080, path="/mcp")


if __name__ == "__main__":
    main()
