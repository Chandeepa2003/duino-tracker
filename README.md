# Duino.lk Inventory Velocity Tracker 📊

Automated stock level tracker for [duino.lk](https://www.duino.lk). Scrapes exact stock counts for all products using WooCommerce cart validation, tracks inventory changes over time, and generates velocity reports.

## How It Works

1. **Sitemap Parsing** — Fetches all product URLs from the WooCommerce sitemap
2. **Stock Checking** — For each product, attempts to add 9999 units to cart. The error message reveals the exact stock count (e.g. "only 42 remaining")
3. **Batching** — Products are split into 5 daily batches (~1080 each) to stay within CI time limits
4. **Reporting** — Compares stock levels across scan dates to calculate sales velocity

## GitHub Actions (Automated)

Runs daily at **5:30 AM Sri Lanka time** via GitHub Actions. Uses `cloudscraper` to bypass Cloudflare protection from datacenter IPs.

Each day processes a different batch (1/5 of all products). Full catalog coverage every 5 days.

You can also trigger it manually from the **Actions** tab → **Duino.lk Stock Tracker** → **Run workflow**.

## Local Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Test with 10 products
python scraper.py --test

# Scrape a specific number
python scraper.py --limit 50

# Scrape ALL products (no batching)
python scraper.py --all

# Default: uses daily batching (same as CI)
python scraper.py

# Generate velocity report
python report.py
```

## Output

- `data/inventory_log.csv` — Raw stock data (timestamp, product, stock count, status)
- `data/velocity_report.txt` — Sales velocity analysis with top movers

## Project Structure

```
duino_tracker/
├── .github/workflows/scrape.yml   # GitHub Actions daily schedule
├── config.py                       # All settings and constants
├── sitemap_parser.py               # Fetches product URLs from sitemap
├── stock_checker.py                # Checks exact stock via cart trick
├── scraper.py                      # Main orchestrator with batching
├── report.py                       # Velocity analytics and reporting
├── requirements.txt                # Python dependencies
└── data/                           # Output directory (auto-created)
    ├── inventory_log.csv
    └── velocity_report.txt
```
