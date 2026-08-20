"""
Duino.lk Inventory Velocity Tracker - Main Scraper
===================================================
Orchestrates the full scraping pipeline:
  1. Fetches all product URLs from the sitemap
  2. Checks stock for each product
  3. Writes results to the CSV log
"""

import csv
import os
import sys
import time
import random
import signal
import datetime
import requests

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


def run(limit=None):
    """
    Main scraper execution.
    
    Args:
        limit: If set, only scrape this many products (for testing).
    """
    global _interrupted
    
    print("=" * 60)
    print("  DUINO.LK INVENTORY VELOCITY TRACKER")
    print("=" * 60)
    
    # ─── Step 1: Get all product URLs ────────────────────────────────
    urls = sitemap_parser.fetch_product_urls()
    if not urls:
        print("[ERROR] No URLs found. Aborting.")
        sys.exit(1)
    
    if limit:
        urls = urls[:limit]
        print(f"[TEST MODE] Limiting to first {limit} products.")
    
    total = len(urls)
    print(f"\nTotal products to scan: {total}")
    print(f"Estimated time: ~{total * 2 // 60} minutes\n")
    
    # ─── Step 2: Set up session ──────────────────────────────────────
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    ensure_csv_exists()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ─── Step 3: Scrape each product ─────────────────────────────────
    results = []
    success_count = 0
    error_count = 0
    oos_count = 0
    variable_count = 0
    
    for i, url in enumerate(urls, 1):
        if _interrupted:
            break
        
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
        
        # Rotate User-Agent every 100 requests
        if i % 100 == 0:
            session.headers["User-Agent"] = random.choice(config.USER_AGENTS)
    
    # ─── Step 4: Write remaining results ─────────────────────────────
    if results:
        append_to_csv(results)
    
    # ─── Summary ─────────────────────────────────────────────────────
    print(f"\n\n{'=' * 60}")
    print(f"  SCRAPE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Timestamp:      {timestamp}")
    print(f"  Products Scanned: {i}")
    print(f"  In Stock:       {success_count}")
    print(f"  Out of Stock:   {oos_count}")
    print(f"  Variable:       {variable_count}")
    print(f"  Errors:         {error_count}")
    print(f"  Data saved to:  {config.CSV_FILE}")
    print(f"{'=' * 60}")
    
    if _interrupted:
        print("\n[!] Scrape was interrupted. Partial results saved.")
        sys.exit(1)


if __name__ == "__main__":
    # Check for --limit flag for testing
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    
    # Check for --test flag (shortcut for --limit 10)
    if "--test" in sys.argv:
        limit = 10
    
    run(limit=limit)
