"""Small build-time customizations for the public documentation site."""

import os
import re

from mkdocs.plugins import event_priority


# Who runs this deployment, who to ask, when its terms and privacy notice last
# changed, and which models it uses.  The tracked pages name no institution,
# so these four are the deployment's to set (docs/customizing.md).  The
# defaults read as sentences, so an unset one never breaks a page; it only
# says less than a real notice should.  docs/corpus.py carries the same table.
POLICY_SLOTS = {
    "{{OPERATOR}}": ("OPERATOR_NAME", "your institution"),
    "{{CONTACT}}": ("OPERATOR_CONTACT",
                    "Ask your instructor, or ask any guide in the {{PLATFORM}} chat to file a report.  "
                    "It reaches the people who run the platform."),
    "{{POLICY_DATE}}": ("POLICY_DATE", "a date this deployment has not set"),
    "{{MODEL_NOTICE}}": ("MODEL_NOTICE",
                         "This deployment has not published which models it uses or where they run, "
                         "so ask your instructor."),
}


# A policy page can carry a box for the institution adopting it: what the
# generic draft already does, and what is theirs to do before publishing.  It
# sits between these two markers and is shown until the deployment dates its
# policy (POLICY_DATE).  Dating it is the act of adopting it, and the box goes.
_UNTIL_ADOPTED = re.compile(r"<!-- until-adopted -->.*?<!-- /until-adopted -->\n*", re.S)


def until_adopted(text: str) -> str:
    return _UNTIL_ADOPTED.sub("", text) if os.environ.get("POLICY_DATE", "").strip() else text


def _public_brand(value: str) -> str:
    """Fill {{PLATFORM}} with the deployment's name for the platform.

    Reader-facing pages never name the platform outright (docs/corpus.py
    refuses them if they do), so one variable names it on the site and in the
    guides alike.  DOCS_PRODUCT_NAME is the older, site-only spelling.
    """
    product = (os.environ.get("PLATFORM_NAME") or os.environ.get("DOCS_PRODUCT_NAME")
               or "aLLManac").strip()
    model = os.environ.get("CHAT_MODEL", "almanac-chat").strip()
    # The policy pages' slots (apex/terms.md, apex/privacy.md) are filled
    # first: a deployment's contact line may itself say {{PLATFORM}}.
    value = until_adopted(value)
    for slot, (env, default) in POLICY_SLOTS.items():
        value = value.replace(slot, (os.environ.get(env) or default).strip())
    return value.replace("{{PLATFORM}}", product).replace("{{MODEL}}", model)


def _brand_page(page) -> None:
    page.title = _public_brand(page.title)
    for key in ("title", "description"):
        if isinstance(page.meta.get(key), str):
            page.meta[key] = _public_brand(page.meta[key])


@event_priority(100)
def on_page_markdown(markdown, page, **_kwargs):
    # Run before the tags/search plugins snapshot page metadata. Rebranding
    # only the rendered Markdown would leave the repository name in indexes.
    _brand_page(page)
    return _public_brand(markdown)


def on_page_context(context, page, **_kwargs):
    _brand_page(page)
    return context
