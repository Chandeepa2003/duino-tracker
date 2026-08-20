"""
Duino.lk Inventory Velocity Tracker - Stock Checker
====================================================
Core engine that checks the exact stock level for a single product
by exploiting the WooCommerce cart quantity validation.
"""

import requests
import re
from bs4 import BeautifulSoup
import config


def check_stock(session, url):
    """
    Check the exact stock level of a single product on duino.lk.
    
    Strategy:
        1. GET the product page to find the product title and WooCommerce product ID.
        2. POST with quantity=9999 to trigger the stock limit error.
        3. Parse the error message for the exact remaining count.
    
    Args:
        session: requests.Session with headers already set.
        url: Full product URL.
    
    Returns:
        dict with keys: url, slug, title, stock_count, status
              status is one of: 'in_stock', 'out_of_stock', 'variable', 'error'
    """
    slug = url.rstrip('/').split('/')[-1]
    result = {
        "url": url,
        "slug": slug,
        "title": "",
        "stock_count": -1,
        "status": "error"
    }
    
    try:
        # ─── Step 1: GET the product page ────────────────────────────
        resp = session.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h1', class_='product_title')
        if title_elem:
            result["title"] = title_elem.text.strip()
        else:
            # Fallback: try <title> tag
            title_tag = soup.find('title')
            result["title"] = title_tag.text.strip().split('–')[0].strip() if title_tag else slug
        
        # Check for variable products (products with options like size/color)
        # These have a <form class="variations_form"> instead of a simple add-to-cart
        variations_form = soup.find('form', class_='variations_form')
        if variations_form:
            result["status"] = "variable"
            result["stock_count"] = -1
            return result
        
        # Find the add-to-cart button to get the WooCommerce product ID
        add_btn = soup.find('button', attrs={'name': 'add-to-cart'})
        if not add_btn:
            # No add-to-cart button = product is out of stock or external
            result["status"] = "out_of_stock"
            result["stock_count"] = 0
            return result
        
        product_id = add_btn.get('value')
        if not product_id:
            result["status"] = "error"
            return result
        
        # ─── Step 2: POST with quantity=9999 ─────────────────────────
        post_data = {
            'quantity': config.CART_QUANTITY,
            'add-to-cart': product_id
        }
        post_resp = session.post(url, data=post_data, timeout=config.REQUEST_TIMEOUT)
        post_soup = BeautifulSoup(post_resp.text, 'html.parser')
        
        # ─── Step 3: Parse the error response ────────────────────────
        error_notices = post_soup.find_all(class_='woocommerce-error')
        for notice in error_notices:
            text = notice.text.strip()
            # Pattern: "(XXX remaining)" where XXX is the stock count
            match = re.search(r'\((\d+)\s+remaining\)', text)
            if match:
                result["stock_count"] = int(match.group(1))
                result["status"] = "in_stock"
                return result
        
        # If we got a success message, stock is >= 9999 (very unlikely but handle it)
        success_notices = post_soup.find_all(class_='woocommerce-message')
        for notice in success_notices:
            if str(config.CART_QUANTITY) in notice.text:
                result["stock_count"] = config.CART_QUANTITY
                result["status"] = "in_stock"
                return result
        
        # Check if the product was actually added (stock might be exactly 9999 or unlimited)
        # Look for "has been added to your cart" message
        for notice in success_notices:
            if 'added to your cart' in notice.text.lower():
                result["stock_count"] = config.CART_QUANTITY
                result["status"] = "in_stock"
                return result
        
        # Fallback: couldn't determine stock
        result["status"] = "error"
        return result
        
    except requests.Timeout:
        result["status"] = "error"
        result["title"] = result["title"] or slug
        return result
    except requests.RequestException as e:
        result["status"] = "error"
        result["title"] = result["title"] or slug
        return result
    except Exception as e:
        result["status"] = "error"
        result["title"] = result["title"] or slug
        return result


if __name__ == "__main__":
    import random
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(config.USER_AGENTS)
    })
    
    # Test with a few known products
    test_urls = [
        "https://www.duino.lk/product/java-robot-car-kit/",
        "https://www.duino.lk/product/servo-motor-sg90-9g/",
        "https://www.duino.lk/product/male-to-male-jumper-wire-30cm/",
    ]
    
    for url in test_urls:
        print(f"\nChecking: {url}")
        result = check_stock(session, url)
        print(f"  Title:  {result['title']}")
        print(f"  Stock:  {result['stock_count']}")
        print(f"  Status: {result['status']}")
