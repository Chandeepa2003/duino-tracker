# Duino.lk Inventory Velocity Tracker

Automatically tracks the **exact stock levels** of every product on [duino.lk](https://www.duino.lk/) and identifies the fastest-moving items.

## How It Works

1. **Product Discovery**: The sitemap parser fetches `product-sitemap.xml` to discover all ~5,400 product URLs.
2. **Stock Extraction**: For each product, the script sends a hidden POST request attempting to add 9,999 units to the cart. WooCommerce rejects this and reveals the exact remaining stock (e.g., *"271 remaining"*).
3. **Data Logging**: Stock levels are appended to `data/inventory_log.csv` with a timestamp.
4. **Velocity Analysis**: After 2+ days of data, the report script calculates how many units each product sold and ranks them.

## Usage

### Run Locally (One-Time)
```bash
# Full scan (~90 minutes for 5,400 products)
python scraper.py

# Quick test (first 10 products only)
python scraper.py --test

# Custom limit
python scraper.py --limit 50
```

### View Report
```bash
python report.py
```

### Automated (GitHub Actions)
Push this repo to GitHub and the scraper will run automatically every day at 5:30 AM Sri Lanka time. Check the **Actions** tab to monitor runs.

## Project Structure
```
├── config.py             # Configuration constants
├── sitemap_parser.py     # Product URL discovery
├── stock_checker.py      # Stock extraction engine
├── scraper.py            # Main orchestrator
├── report.py             # Analytics & reports
├── requirements.txt      # Python dependencies
├── data/
│   ├── inventory_log.csv # Stock data (auto-generated)
│   └── velocity_report.txt
└── .github/workflows/
    └── scrape.yml        # GitHub Actions automation
```

## Requirements
- Python 3.8+
- `pip install -r requirements.txt`
