"""Small build-time customizations for the public documentation site."""

import os

from mkdocs.plugins import event_priority


def _public_brand(value: str) -> str:
    """Replace the repository name only when a deployment requests it.

    The source Markdown remains the generic project corpus used by RAG.  A
    site can publish the same pages under its own public name without keeping
    a fork or rewriting the source before every build.
    """
    product = os.environ.get("DOCS_PRODUCT_NAME", "").strip()
    if not product:
        return value
    return (
        value.replace("The aLLManac", product)
        .replace("the aLLManac", product)
        .replace("aLLManac", product)
    )


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
