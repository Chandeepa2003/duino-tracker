"""
Duino.lk Inventory Velocity Tracker - Sitemap Parser
=====================================================
Fetches the WooCommerce product sitemap XML and extracts
every product URL into a clean Python list.
"""

import requests
import re
import config


def fetch_product_urls():
    """
    Fetch the product sitemap from duino.lk and return a list of all
    product URLs found in <loc> elements.
    
    Returns:
        list[str]: List of product URLs (e.g. ['https://www.duino.lk/product/...', ...])
    """
    print(f"Fetching sitemap from {config.SITEMAP_URL} ...")
    
    try:
        response = requests.get(
            config.SITEMAP_URL,
            timeout=config.REQUEST_TIMEOUT,
            headers={"User-Agent": config.USER_AGENTS[0]}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch sitemap: {e}")
        return []

    # Parse <loc> tags using regex (faster than XML parser for this simple case)
    # Pattern matches: <loc><![CDATA[URL]]></loc>  OR  <loc>URL</loc>
    urls = re.findall(r'<loc>\s*(?:<!\[CDATA\[)?(https://www\.duino\.lk/product/[^<\]]+)(?:\]\]>)?\s*</loc>', response.text)
    
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
