"""
Duino.lk Inventory Velocity Tracker - Main Scraper
===================================================
Orchestrates the full scraping pipeline:
  1. Fetches all product URLs from the sitemap
  2. Selects today's batch (for CI) or all products (for local)
  3. Checks stock for each product
  4. Writes results to the CSV log

Batching Strategy:
  Products are split into BATCH_COUNT groups. Each daily run
  processes one batch, cycling through all products over N days.
  The batch is determined by: day_of_year % BATCH_COUNT
"""

import csv
import os
import sys
import time
import random
import signal
import datetime

import config
import sitemap_parser
import stock_checker


# ─── Graceful Shutdown ───────────────────────────────────────────────
_interrupted = False

def _signal_handler(sig, frame):
    global _interrupted
    print("\n[!] Interrupt received. Saving progress and exiting...")
    _interrupted = True

signal.signal(signal.SIGINT, _signal_handler)


def _create_session():
    """
    Create a session capable of bypassing Cloudflare.
    Falls back to plain requests if cloudscraper is unavailable.
    """
    try:
        import cloudscraper
        session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
            }
        )
        return session
    except ImportError:
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(config.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        return session


def ensure_csv_exists():
    """Create the data directory and CSV file with headers if they don't exist."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if not os.path.isfile(config.CSV_FILE):
        with open(config.CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(config.CSV_COLUMNS)


def append_to_csv(rows):
    """Append a list of row-dicts to the CSV file."""
    with open(config.CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([
                row["timestamp"],
                row["slug"],
                row["title"],
                row["stock_count"],
                row["status"]
            ])


def get_todays_batch(urls, batch_count):
    """
    Determine which batch of products to scrape today.
    Uses day-of-year modulo to cycle through batches automatically.

    Returns:
        (batch_urls, batch_index, total_batches)
    """
    day_of_year = datetime.datetime.now(datetime.timezone.utc).timetuple().tm_yday
    batch_index = day_of_year % batch_count
    batch_size = len(urls) // batch_count
    start = batch_index * batch_size
    # Last batch gets any remainder products
    end = start + batch_size if batch_index < batch_count - 1 else len(urls)
    return urls[start:end], batch_index, batch_count


def run(limit=None, batch_mode=True):
    """
    Main scraper execution.

    Args:
        limit: If set, only scrape this many products (for testing).
        batch_mode: If True, only scrape today's batch. If False, scrape all.
    """
    global _interrupted

    print("=" * 60)
    print("  DUINO.LK INVENTORY VELOCITY TRACKER")
    print("=" * 60)

    # ─── Step 1: Get all product URLs ────────────────────────────────
    session = _create_session()
    urls = sitemap_parser.fetch_product_urls(session)

    if not urls:
        print("[ERROR] No URLs found from sitemap.")
        print("  This usually means Cloudflare is blocking the request.")
        print("  The workflow will continue without scraping.")
        # Exit with 0 so GitHub Actions doesn't mark the workflow as failed
        sys.exit(0)

    # ─── Step 2: Select products to scrape ───────────────────────────
    if limit:
        urls = urls[:limit]
        print(f"[TEST MODE] Limiting to first {limit} products.")
    elif batch_mode and len(urls) > 500:
        batch_urls, batch_idx, total_batches = get_todays_batch(urls, config.BATCH_COUNT)
        print(f"\n[BATCH MODE] Day batch {batch_idx + 1}/{total_batches}")
        print(f"  Total products in catalog: {len(urls)}")
        print(f"  Products in this batch:    {len(batch_urls)}")
        print(f"  Full catalog coverage in:  {total_batches} days")
        urls = batch_urls
    else:
        print(f"[FULL MODE] Scraping all {len(urls)} products.")

    total = len(urls)
    print(f"\nProducts to scan: {total}")
    est_minutes = total * 2 // 60
    print(f"Estimated time: ~{est_minutes} minutes\n")

    # ─── Step 3: Set up CSV and timestamp ────────────────────────────
    ensure_csv_exists()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # ─── Step 4: Scrape each product ─────────────────────────────────
    results = []
    success_count = 0
    error_count = 0
    oos_count = 0
    variable_count = 0
    scanned = 0

    for i, url in enumerate(urls, 1):
        if _interrupted:
            break

        scanned = i
        slug = sitemap_parser.get_slug_from_url(url)

        # Progress bar
        pct = (i / total) * 100
        bar_len = 30
        filled = int(bar_len * i / total)
        bar = '#' * filled + '-' * (bar_len - filled)
        status_text = slug[:40]
        try:
            print(f"\r  [{bar}] {pct:5.1f}% ({i}/{total}) {status_text:<40s}", end='', flush=True)
        except UnicodeEncodeError:
            print(f"\r  [{bar}] {pct:5.1f}% ({i}/{total})", end='', flush=True)

        # Retry logic
        result = None
        for attempt in range(config.MAX_RETRIES + 1):
            result = stock_checker.check_stock(session, url)
            if result["status"] != "error":
                break
            if attempt < config.MAX_RETRIES:
                time.sleep(2)  # Wait before retry

        # Record result
        result["timestamp"] = timestamp
        results.append(result)

        # Stats
        if result["status"] == "in_stock":
            success_count += 1
        elif result["status"] == "out_of_stock":
            oos_count += 1
        elif result["status"] == "variable":
            variable_count += 1
        else:
            error_count += 1

        # Batch write every 50 products to prevent data loss
        if len(results) >= 50:
            append_to_csv(results)
            results = []

        # Randomized delay between requests
        delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
        time.sleep(delay)

        # Rotate User-Agent every 100 requests (for plain requests sessions)
        if i % 100 == 0:
            try:
                session.headers["User-Agent"] = random.choice(config.USER_AGENTS)
            except Exception:
                pass  # cloudscraper manages its own headers

    # ─── Step 5: Write remaining results ─────────────────────────────
    if results:
        append_to_csv(results)

    # ─── Summary ─────────────────────────────────────────────────────
    print(f"\n\n{'=' * 60}")
    print(f"  SCRAPE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Timestamp:        {timestamp}")
    print(f"  Products Scanned: {scanned}")
    print(f"  In Stock:         {success_count}")
    print(f"  Out of Stock:     {oos_count}")
    print(f"  Variable:         {variable_count}")
    print(f"  Errors:           {error_count}")
    print(f"  Data saved to:    {config.CSV_FILE}")
    print(f"{'=' * 60}")

    if _interrupted:
        print("\n[!] Scrape was interrupted. Partial results saved.")
        sys.exit(1)


if __name__ == "__main__":
    # Parse CLI arguments
    limit = None
    batch_mode = True  # Default: batching ON (safe for CI)

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
        batch_mode = False

    # --test: shortcut for --limit 10
    if "--test" in sys.argv:
        limit = 10
        batch_mode = False

    # --all: scrape everything (for local full scan)
    if "--all" in sys.argv:
        batch_mode = False

    run(limit=limit, batch_mode=batch_mode)
