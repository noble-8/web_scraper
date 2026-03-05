import os
import re
import json
import uuid
import argparse
import time
import urllib.parse
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Constants
AMAZON_URL = "https://www.amazon.com/gp/css/order-history?ref_=nav_AccountFlyout_orders"

def setup_argparse():
    parser = argparse.ArgumentParser(description="Amazon Mobile Order Scraper")
    parser.add_argument("--months", type=int, default=1, help="Number of months of order history to scrape")
    parser.add_argument("--output", type=str, default="transactions.json", help="Output JSON file path")
    parser.add_argument("--headful", action="store_true", help="Run with visible browser (useful for solving captchas manually)")
    parser.add_argument("--use-brave", action="store_true", help="Launch Brave with your existing profile to skip login. MUST CLOSE ALL BRAVE WINDOWS FIRST.")
    return parser.parse_args()

def login_to_amazon(page, email, password):
    # Check if we are redirected to the sign-in page
    if "signin" in page.url.lower():
        if not email or not password:
            print("You are on the sign-in page, but credentials aren't provided in .env.")
            print("Please log in manually in the browser. Waiting up to 2 minutes...")
            try:
                page.wait_for_url("**/order-history*", timeout=120000)
                print("Successfully logged in manually.")
                return
            except Exception as e:
                raise Exception("Did not navigate to order history in time.") from e
        else:
            print("Logging in...")
            # Email step
            email_input = page.locator("input[type='email'], input[name='email'], input[type='text']").locator("visible=true").first
            email_input.wait_for(state="visible", timeout=60000)
            email_input.fill(email)
            
            continue_btn = page.locator("input#continue, input[type='submit']").locator("visible=true").first
            continue_btn.click()
            
            # Password step
            password_input = page.locator("input[type='password'], input[name='password']").locator("visible=true").first
            password_input.wait_for(state="visible", timeout=60000)
            password_input.fill(password)
            
            submit_btn = page.locator("input#signInSubmit, input[type='submit']").locator("visible=true").first
            submit_btn.click()
        
        # Wait for navigation. If a captcha or OTP is triggered, the URL won't change to order history
        try:
            page.wait_for_url("**/your-orders/orders*", timeout=15000)
            print("Successfully logged in.")
        except Exception as e:
            # Maybe it went to the old order-history, let's check current URL
            if "order-history" in page.url.lower() or "your-orders" in page.url.lower():
                print("Successfully logged in.")
                return
            
            print("Login took too long or encountered anti-bot measures (CAPTCHA/OTP).")
            print("Current URL:", page.url)
            print("If you ran with --headful, you can manually solve it. Waiting up to 120 seconds...")
            # Give the user a chance to manually solve it if they are running headful
            for _ in range(120):
                if "order-history" in page.url.lower() or "your-orders" in page.url.lower():
                    print("Successfully bypassed or solved login challenge.")
                    break
                time.sleep(1)
            else:
                raise Exception("Failed to bypass login anti-bot protections.") from e

def extract_transaction_details(page, order_card_url):
    """
    Since getting granular details like exact tax, subtotal, and card info requires visiting the order details,
    we navigate to each order's specific summary page using the mobile DOM.
    """
    txn = {
        "id": str(uuid.uuid4()),
        "external_id": None,
        "datetime": datetime.now(timezone.utc).isoformat(),
        "url": order_card_url,
        "order_status": "COMPLETED",  # fallback
        "shipping": {
            "location": {
                "address": {
                    "line1": None,
                    "line2": None,
                    "city": None,
                    "region": None,
                    "postal_code": None,
                    "country": None
                },
                "first_name": None,
                "last_name": None
            }
        },
        "payment_methods": [
            {
                "external_id": None,
                "type": "CARD",
                "brand": "OTHER",
                "last_four": None,
                "name": None,
                "transaction_amount": "0.00"
            }
        ],
        "price": {
            "sub_total": "0.00",
            "adjustments": [
                {
                    "type": "TAX",
                    "label": "Tax",
                    "amount": "0.00"
                }
            ],
            "total": "0.00",
            "currency": "USD"
        },
        "products": []
    }
    
    page.goto(order_card_url, wait_until="domcontentloaded")
    
    # Extract Order ID
    try:
        order_id_elem = page.locator("xpath=//*[contains(text(), 'Order #')]").first
        if order_id_elem.count() > 0:
            raw_text = order_id_elem.inner_text().replace('Order #', '').strip()
            txn["external_id"] = raw_text
    except Exception:
        pass
        
    # Extract Order Date / Datetime
    try:
        # Approximate: "Order placed on January 1, 2024"
        date_elem = page.locator("xpath=//*[contains(text(), 'Order placed')]").first
        if date_elem.count() > 0:
            date_str = date_elem.inner_text().replace('Order placed', '').strip()
            # Try to parse it
            dt = datetime.strptime(date_str, "%B %d, %Y")
            txn["datetime"] = dt.replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        txn["datetime"] = datetime.now(timezone.utc).isoformat()
        
    try:
        page_text = page.locator("body").inner_text()
    except Exception:
        page_text = ""

    # Extract Total 
    try:
        total_match = re.search(r'(?:Grand Total|Order Total|Total(?: before tax)?)[^\$]*\$([0-9,.]+)', page_text, re.IGNORECASE)
        if total_match:
            raw_total = total_match.group(1).replace(',', '')
            txn["price"]["total"] = raw_total
            txn["price"]["sub_total"] = raw_total
        else:
            total_elem = page.locator(".a-color-price").first
            if total_elem.count() > 0:
                raw_total = total_elem.inner_text().replace('$', '').strip()
                txn["price"]["total"] = raw_total
                txn["price"]["sub_total"] = raw_total
                
        # Update payment method transaction amount to match the total
        txn["payment_methods"][0]["transaction_amount"] = txn["price"]["total"]
    except Exception:
        pass

    # Extract Shipping Details
    try:
        addr_match = re.search(r'(?:Shipping|Delivery) Address[^\n]*\n([^\n]+)\n([^\n]+)\n([^,]+,\s*[A-Z]{2}\s*\d{5})', page_text, re.IGNORECASE)
        if addr_match:
            name_parts = addr_match.group(1).strip().split(' ', 1)
            txn["shipping"]["location"]["first_name"] = name_parts[0] if len(name_parts) > 0 else ""
            txn["shipping"]["location"]["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
            
            txn["shipping"]["location"]["address"]["line1"] = addr_match.group(2).strip()
            
            city_state_zip = addr_match.group(3).strip()
            csz_match = re.search(r'(.*?),\s*([A-Z]{2})\s*(\d{5})', city_state_zip)
            if csz_match:
                txn["shipping"]["location"]["address"]["city"] = csz_match.group(1).strip()
                txn["shipping"]["location"]["address"]["region"] = csz_match.group(2).strip()
                txn["shipping"]["location"]["address"]["postal_code"] = csz_match.group(3).strip()
                txn["shipping"]["location"]["address"]["country"] = "US"
    except Exception:
        pass
        
    # Payment Method Details
    try:
        cc_match = re.search(r'(?:Visa|MasterCard|AMEX|Discover|Credit Card|American Express)[^\d]*ending in (\d{4})', page_text, re.IGNORECASE)
        if cc_match:
            txn["payment_methods"][0]["last_four"] = cc_match.group(1)
            brand_match = re.search(r'(Visa|MasterCard|AMEX|Discover|American Express|Credit Card)', page_text[max(0, cc_match.end() - 50):cc_match.end()], re.IGNORECASE)
            if brand_match:
                txn["payment_methods"][0]["brand"] = brand_match.group(1).upper().replace('AMERICAN EXPRESS', 'AMEX')
    except Exception:
        pass

    # Try finding items
    item_links = page.locator("a[href*='/dp/']")
    seen_asins = set()
    
    # Pre-parse valid products to count them for price division
    valid_products = []
    
    for i in range(item_links.count()):
        href = item_links.nth(i).get_attribute("href")
        if not href:
            continue
            
        asin = None
        if '/dp/' in href:
            raw_asin = href.split('/dp/')[1].split('/')[0].split('?')[0] # Remove query params
            if len(raw_asin) >= 10:
                asin = raw_asin[:10] # Ensure strict 10 char ASIN
                
        if not asin or asin in seen_asins:
            continue
            
        seen_asins.add(asin)
        valid_products.append({"asin": asin})
        
    num_items = len(valid_products) if valid_products else 1
    
    try:
        total_float = float(txn["price"]["total"].replace(',', ''))
        apportioned_price = f"{(total_float / num_items):.2f}"
    except Exception:
        apportioned_price = "0.00"

    for product in valid_products:
        asin = product["asin"]
        
        # Collect all links with this ASIN to get the best text and image
        asin_links = page.locator(f"a[href*='{asin}']")
        name = ""
        image_url = None
        seller_name = None
        
        for j in range(asin_links.count()):
            link = asin_links.nth(j)
            text = link.inner_text().strip()
            if text and len(text) > len(name):
                name = text
            
            img = link.locator("img").first
            if img.count() > 0:
                src = img.get_attribute("src")
                if src and "media-amazon.com" in src:
                    image_url = src
                elif img.get_attribute("data-src") and "media-amazon.com" in img.get_attribute("data-src"):
                    image_url = img.get_attribute("data-src")
                    
        if not name:
            name = f"Amazon Product {asin}"
            
        # Try to find seller in the text block near it or on the page
        seller_match = re.search(r'Sold by:?\s*([^\n]+)', page_text, re.IGNORECASE)
        if seller_match:
            seller_name = seller_match.group(1).strip()
            
        txn["products"].append({
            "external_id": asin,
            "name": name,
            "description": "",
            "url": f"https://www.amazon.com/dp/{asin}",
            "image_url": image_url,
            "quantity": 1,
            "price": {
                "sub_total": apportioned_price,
                "total": apportioned_price,
                "unit_price": apportioned_price
            },
            "seller": {
                "name": seller_name,
                "url": None
            },
            "eligibility": []
        })
        
    return txn


def scrape_orders(page, months_to_scrape):
    transactions = []
    
    # Target date logic
    cutoff_date = datetime.now() - relativedelta(months=months_to_scrape)
    
    # We are currently on the order-history page
    # Amazon Mobile uses different classes. A common container is .yo-order-card or .order-card or simply list items.
    
    print("Scraping order history...")
    
    # Since we can't perfectly predict the exact DOM structure for the user, we will extract all links 
    # pointing to order details and visit them one by one.
    page.wait_for_selector("body")
    # Wait for dynamic content to load
    page.wait_for_timeout(3000)
    
    try:
        page.screenshot(path="debug_orders_page.png", full_page=True)
        with open("debug_orders_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Saved debug_orders_page.png and debug_orders_page.html for inspection.")
    except Exception as e:
        print(f"Warning: Failed to save debug files: {e}")
    
    has_next_page = True
    page_count = 0
    scraped_order_urls = set()
    
    while has_next_page:
        page_count += 1
        print(f"Parsing order history page {page_count}...")
        
        # Scrape all detail links visible on the current mobile list page.
        # Note: Amazon mobile uses various URL schemes for the summary
        links = page.locator("a[href*='orderId='], a[href*='orderID=']")
        
        print(f"Found {links.count()} links containing an order ID on page {page_count}.")
        
        new_urls = []
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if href:
                # Find the order ID using urllib
                try:
                    parsed = urllib.parse.urlparse(href)
                    query = urllib.parse.parse_qs(parsed.query)
                    order_id = query.get("orderId", query.get("orderID", [None]))[0]
                    
                    if order_id:
                        full_url = f"https://www.amazon.com/gp/your-account/order-details?orderID={order_id}"
                        if full_url not in scraped_order_urls:
                            new_urls.append(full_url)
                            scraped_order_urls.add(full_url)
                except Exception as e:
                    pass
                    
        # Visit each new URL and build the node schema
        current_list_url = page.url
        for url in new_urls:
            print(f" -> Scraping order details from {url}")
            try:
                txn = extract_transaction_details(page, url)
                transactions.append(txn)
            except Exception as e:
                print(f"Error extracting {url}: {e}")
                
        # Return to main list
        if new_urls:
            page.goto(current_list_url)
        
        # Pagination: Look for a "Next" or "Load more" button
        try:
            # We look for standard pagination Next link
            next_btn = page.locator("a:has-text('Next')")
            if next_btn.count() > 0 and next_btn.first.is_visible():
                next_btn.first.click()
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2) # rate limit / wait for content
            else:
                has_next_page = False
        except Exception:
            has_next_page = False
            
    print(f"Scrape complete. Extracted {len(transactions)} transactions.")
    return transactions

def main():
    args = setup_argparse()
    
    email = os.getenv("AMAZON_EMAIL")
    password = os.getenv("AMAZON_PASSWORD")
    
    if not email or not password:
        print("WARNING: AMAZON_EMAIL or AMAZON_PASSWORD environment variables not found.")
        print("Please configure them in your .env file.")
        return

    # Start playwright
    with sync_playwright() as p:
        # Require mobile user agent. Selecting an iPhone 13 profile from playwright.
        iphone = p.devices['iPhone 13'].copy()
        iphone.pop('default_browser_type', None)
        
        if args.use_brave:
            user_data_dir = os.path.expanduser("~/.config/BraveSoftware/Brave-Browser")
            executable_path = "/usr/bin/brave-browser"
            if not os.path.exists(executable_path):
                executable_path = "/usr/bin/brave"
                
            print(f"Attempting to launch Brave using your default profile...")
            print(f"Make sure you DO NOT have Brave open right now, otherwise it will fail due to a profile lock.")
            
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    executable_path=executable_path,
                    headless=not args.headful,
                    **iphone
                )
                page = context.pages[0] if context.pages else context.new_page()
            except Exception as e:
                print("\nERROR: Failed to launch Brave with your profile.")
                print("If you see a 'Lock' error, it means you still have a Brave window running. Please close Brave completely first!")
                print(f"Details: {e}")
                return
        else:
            browser = p.chromium.launch(headless=not args.headful)
            context = browser.new_context(**iphone)
            page = context.new_page()
        
        try:
            print("Navigating to Amazon Order History (will redirect to login if not authenticated)...")
            page.goto(AMAZON_URL, wait_until="domcontentloaded")
            login_to_amazon(page, email, password)
            transactions = scrape_orders(page, args.months)
            
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(transactions, f, indent=2)
                
            print(f"Successfully saved results to {args.output}")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if not args.use_brave:
                browser.close()
            else:
                context.close()

if __name__ == "__main__":
    main()
