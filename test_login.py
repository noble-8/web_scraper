import os
from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        iphone = p.devices['iPhone 13'].copy()
        iphone.pop('default_browser_type', None)
        context = browser.new_context(**iphone)
        page = context.new_page()
        page.goto("https://www.amazon.com/gp/css/order-history?ref_=nav_AccountFlyout_orders", wait_until="domcontentloaded")
        
        try:
            page.wait_for_selector("input#ap_email", state="visible", timeout=5000)
            print("Found email input using id='ap_email'")
            page.screenshot(path="login_debug1.png", full_page=True)
        except Exception as e:
            print("Could not find email input using id='ap_email'.")
            page.screenshot(path="login_debug1.png", full_page=True)
            
        with open("login_debug.html", "w") as f:
            f.write(page.content())
        
        browser.close()

if __name__ == "__main__":
    test()
