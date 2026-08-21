"""
Duino.lk Inventory Velocity Tracker - Sitemap Parser
=====================================================
Fetches the WooCommerce product sitemap XML and extracts
every product URL into a clean Python list.

Uses cloudscraper to bypass Cloudflare protection when
running from GitHub Actions datacenter IPs.
"""

import re
import time

import config


def _create_session():
    """
    Create a scraper session that can bypass Cloudflare.
    Falls back to a plain requests session if cloudscraper is unavailable.
    """
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
            }
        )
        print("  [OK] Using cloudscraper session (Cloudflare bypass)")
        return scraper
    except ImportError:
        import requests
        print("  [WARN] cloudscraper not installed, using plain requests")
        session = requests.Session()
        session.headers.update({"User-Agent": config.USER_AGENTS[0]})
        return session


def fetch_product_urls(session=None):
    """
    Fetch the product sitemap from duino.lk and return a list of all
    product URLs found in <loc> elements.

    Includes retry logic for reliability in CI environments.

    Args:
        session: Optional pre-configured session. If None, creates one.

    Returns:
        list[str]: List of product URLs (e.g. ['https://www.duino.lk/product/...', ...])
    """
    print(f"Fetching sitemap from {config.SITEMAP_URL} ...")

    if session is None:
        session = _create_session()

    # ─── Retry loop ──────────────────────────────────────────────────
    response = None
    for attempt in range(config.SITEMAP_RETRIES):
        try:
            response = session.get(
                config.SITEMAP_URL,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            # Sanity check: response should contain XML/sitemap content
            if '<loc>' in response.text or 'CDATA' in response.text:
                break  # Success
            else:
                print(f"  [WARN] Attempt {attempt + 1}: Got response but no sitemap content (possible Cloudflare block)")
                response = None
        except Exception as e:
            print(f"  [WARN] Attempt {attempt + 1}/{config.SITEMAP_RETRIES} failed: {e}")
            response = None

        if attempt < config.SITEMAP_RETRIES - 1:
            wait = config.SITEMAP_RETRY_DELAY * (attempt + 1)
            print(f"  Retrying in {wait}s ...")
            time.sleep(wait)

    if response is None:
        print("[ERROR] Failed to fetch sitemap after all retries.")
        return []

    # ─── Parse <loc> tags using regex ────────────────────────────────
    # Pattern matches: <loc><![CDATA[URL]]></loc>  OR  <loc>URL</loc>
    urls = re.findall(
        r'<loc>\s*(?:<!\[CDATA\[)?(https://www\.duino\.lk/product/[^<\]]+)(?:\]\]>)?\s*</loc>',
        response.text
    )

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        url = url.strip()
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    print(f"Found {len(unique_urls)} unique product URLs in sitemap.")
    return unique_urls


def get_slug_from_url(url):
    """
    Extract the product slug from a duino.lk product URL.

    Example:
        'https://www.duino.lk/product/servo-motor-sg90-9g/' -> 'servo-motor-sg90-9g'
    """
    # Remove trailing slash, then take the last segment
    return url.rstrip('/').split('/')[-1]


if __name__ == "__main__":
    urls = fetch_product_urls()
    if urls:
        print(f"\nFirst 5 URLs:")
        for u in urls[:5]:
            print(f"  {get_slug_from_url(u):50s} -> {u}")
        print(f"\nLast 5 URLs:")
        for u in urls[-5:]:
            print(f"  {get_slug_from_url(u):50s} -> {u}")
