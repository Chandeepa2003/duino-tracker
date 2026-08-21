"""
Duino.lk Inventory Velocity Tracker - Configuration
====================================================
All tunable constants and settings in one place.
"""

import os

# ─── Paths ───────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_FILE = os.path.join(DATA_DIR, "inventory_log.csv")
REPORT_FILE = os.path.join(DATA_DIR, "velocity_report.txt")

# ─── Sitemap ─────────────────────────────────────────────────────────
SITEMAP_URL = "https://www.duino.lk/product-sitemap.xml"

# ─── Scraping Behaviour ─────────────────────────────────────────────
REQUEST_TIMEOUT = 15          # seconds per request
MIN_DELAY = 1.0               # minimum seconds between requests
MAX_DELAY = 3.0               # maximum seconds between requests
MAX_RETRIES = 2                # retry count per product on failure
CART_QUANTITY = 9999           # quantity to attempt adding to cart

# ─── Batching (for GitHub Actions) ──────────────────────────────────
BATCH_COUNT = 5               # split all products into N daily batches
                              # ~1080 products per batch ≈ 45-60 min runtime
SITEMAP_RETRIES = 3           # retry count for sitemap fetch
SITEMAP_RETRY_DELAY = 10      # seconds between sitemap retries

# ─── User-Agent Rotation Pool ───────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ─── CSV Column Names ───────────────────────────────────────────────
CSV_COLUMNS = ["timestamp", "product_slug", "product_name", "stock_count", "status"]
