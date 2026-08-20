"""
Duino.lk Inventory Velocity Tracker - Analytics & Report
=========================================================
Reads the inventory_log.csv and calculates sales velocity
for each product across consecutive scan dates.
"""

import csv
import os
import datetime
from collections import defaultdict

import config


def load_data():
    """
    Load the CSV and return a structured dict:
        { product_slug: [ (timestamp, title, stock_count, status), ... ] }
    Sorted by timestamp ascending within each product.
    """
    if not os.path.isfile(config.CSV_FILE):
        print(f"[ERROR] No data file found at {config.CSV_FILE}")
        print("  Run scraper.py first to collect data.")
        return {}
    
    data = defaultdict(list)
    
    with open(config.CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = row.get("product_slug", "")
            if not slug:
                continue
            
            try:
                stock = int(row.get("stock_count", -1))
            except ValueError:
                stock = -1
            
            data[slug].append({
                "timestamp": row.get("timestamp", ""),
                "title": row.get("product_name", slug),
                "stock_count": stock,
                "status": row.get("status", "error")
            })
    
    # Sort each product's entries by timestamp
    for slug in data:
        data[slug].sort(key=lambda x: x["timestamp"])
    
    return dict(data)


def calculate_velocity(data):
    """
    For each product, compare consecutive scan dates and calculate:
      - total_sold: sum of all positive stock decreases
      - times_restocked: count of times stock increased
      - went_oos: True if ever went from >0 to 0
      - latest_stock: most recent stock count
      - first_stock: earliest stock count
      - scan_count: number of data points
    """
    results = []
    
    for slug, entries in data.items():
        # Filter to only in_stock entries for velocity calculation
        stock_entries = [e for e in entries if e["status"] in ("in_stock", "out_of_stock") and e["stock_count"] >= 0]
        
        if not stock_entries:
            continue
        
        title = stock_entries[-1]["title"]
        latest_stock = stock_entries[-1]["stock_count"]
        first_stock = stock_entries[0]["stock_count"]
        first_time = stock_entries[0]["timestamp"]
        latest_time = stock_entries[-1]["timestamp"]
        
        total_sold = 0
        times_restocked = 0
        went_oos = False
        
        for i in range(1, len(stock_entries)):
            prev = stock_entries[i - 1]["stock_count"]
            curr = stock_entries[i]["stock_count"]
            
            diff = prev - curr
            
            if diff > 0:
                total_sold += diff  # Stock decreased = units sold
            elif diff < 0:
                times_restocked += 1  # Stock increased = restocked
            
            if prev > 0 and curr == 0:
                went_oos = True
        
        # Calculate days between first and last scan
        try:
            t1 = datetime.datetime.strptime(first_time, "%Y-%m-%d %H:%M:%S")
            t2 = datetime.datetime.strptime(latest_time, "%Y-%m-%d %H:%M:%S")
            days_tracked = max((t2 - t1).days, 1)
        except ValueError:
            days_tracked = 1
        
        avg_daily_sales = round(total_sold / days_tracked, 2) if days_tracked > 0 else 0
        
        results.append({
            "slug": slug,
            "title": title,
            "total_sold": total_sold,
            "avg_daily_sales": avg_daily_sales,
            "times_restocked": times_restocked,
            "went_oos": went_oos,
            "latest_stock": latest_stock,
            "first_stock": first_stock,
            "scan_count": len(stock_entries),
            "days_tracked": days_tracked,
        })
    
    # Sort by total_sold descending
    results.sort(key=lambda x: x["total_sold"], reverse=True)
    return results


def generate_report(top_n=50):
    """Generate and print the velocity report."""
    data = load_data()
    if not data:
        return
    
    velocity = calculate_velocity(data)
    
    total_products = len(velocity)
    products_with_sales = sum(1 for v in velocity if v["total_sold"] > 0)
    total_units_sold = sum(v["total_sold"] for v in velocity)
    
    # ─── Console Report ──────────────────────────────────────────────
    report_lines = []
    
    def out(line=""):
        print(line)
        report_lines.append(line)
    
    out("=" * 90)
    out("  DUINO.LK INVENTORY VELOCITY REPORT")
    out(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out("=" * 90)
    out(f"  Total Products Tracked:    {total_products}")
    out(f"  Products with Sales:       {products_with_sales}")
    out(f"  Total Units Sold:          {total_units_sold}")
    out("")
    
    if not velocity or velocity[0]["total_sold"] == 0:
        out("  [INFO] No stock movement detected yet.")
        out("  You need at least 2 scan dates to detect changes.")
        out("  Run the scraper again tomorrow to start seeing results!")
        out("=" * 90)
    else:
        out(f"  TOP {min(top_n, products_with_sales)} FASTEST-MOVING ITEMS")
        out("-" * 90)
        out(f"  {'#':<4} {'Product Name':<45} {'Sold':>6} {'Avg/Day':>8} {'Stock':>6} {'Restocks':>8}")
        out("-" * 90)
        
        rank = 0
        for v in velocity[:top_n]:
            if v["total_sold"] == 0:
                break
            rank += 1
            name = v["title"][:43]
            out(f"  {rank:<4} {name:<45} {v['total_sold']:>6} {v['avg_daily_sales']:>8.1f} {v['latest_stock']:>6} {v['times_restocked']:>8}")
        
        out("-" * 90)
        
        # Out of Stock products
        oos_products = [v for v in velocity if v["went_oos"]]
        if oos_products:
            out(f"\n  PRODUCTS THAT WENT OUT OF STOCK ({len(oos_products)})")
            out("-" * 90)
            for v in oos_products[:20]:
                name = v["title"][:60]
                out(f"    • {name} (sold {v['total_sold']} units)")
            out("-" * 90)
        
        out("=" * 90)
    
    # ─── Save to file ────────────────────────────────────────────────
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"\n  Report saved to: {config.REPORT_FILE}")


if __name__ == "__main__":
    generate_report()
