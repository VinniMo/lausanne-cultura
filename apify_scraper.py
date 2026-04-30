"""Apify-powered fallback scraper for JS-heavy sites.

Activated only when ``APIFY_API_KEY`` is set. A single batched run renders
multiple URLs through ``apify/website-content-crawler`` and returns
``{url: rendered_html}``; callers re-use the existing JSON-LD / HTML
extractors on that rendered output.
"""
from __future__ import annotations

import logging
from typing import Iterable

from config import config

logger = logging.getLogger(__name__)

ACTOR_ID = "apify/website-content-crawler"


def is_enabled() -> bool:
    return bool(config.APIFY_API_KEY)


def fetch_many(urls: Iterable[str]) -> dict[str, str]:
    """Render *urls* via Apify in a single run; return {url: html}.

    Returns an empty dict on any error or when Apify is not configured.
    """
    url_list = [u for u in urls if u]
    if not url_list or not is_enabled():
        return {}

    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.warning("apify-client not installed; skipping Apify fallback")
        return {}

    client = ApifyClient(config.APIFY_API_KEY)
    run_input = {
        "startUrls": [{"url": u} for u in url_list],
        "maxCrawlDepth": 0,
        "maxCrawlPages": len(url_list),
        "crawlerType": "playwright:firefox",
        "saveHtml": True,
        "saveMarkdown": False,
        "removeCookieWarnings": True,
    }

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input, timeout_secs=300)
    except Exception:
        logger.exception("Apify actor run failed")
        return {}

    if not run or "defaultDatasetId" not in run:
        return {}

    rendered: dict[str, str] = {}
    try:
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            url = item.get("url") or item.get("loadedUrl")
            html = item.get("html")
            if url and html:
                rendered[url] = html
    except Exception:
        logger.exception("Failed to read Apify dataset")
        return {}

    logger.info("Apify rendered %d / %d URLs", len(rendered), len(url_list))
    return rendered
