"""Small build-time customizations for the public documentation site."""

import os

from mkdocs.plugins import event_priority


def _public_brand(value: str) -> str:
    """Fill {{PLATFORM}} with the deployment's name for the platform.

    Reader-facing pages never name the platform outright (docs/corpus.py
    refuses them if they do), so one variable names it on the site and in the
    guides alike.  DOCS_PRODUCT_NAME is the older, site-only spelling.
    """
    product = (os.environ.get("PLATFORM_NAME") or os.environ.get("DOCS_PRODUCT_NAME")
               or "aLLManac").strip()
    model = os.environ.get("CHAT_MODEL", "almanac-chat").strip()
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
