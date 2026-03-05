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
        
        email = "Jandobellsmom12@icloud.com"
        
        email_selectors = ["input[name='email']", "input[type='email']"]
        success = False
        for sel in email_selectors:
            try:
                page.locator(sel).first.wait_for(state="visible", timeout=5000)
                page.locator(sel).first.fill(email)
                print(f"Successfully filled email using {sel}")
                success = True
                break
            except Exception as e:
                print(f"Failed with {sel}: {e}")
                
        if not success:
            print("Failed to fill email completely.")
                
        try:
            page.locator("input#continue").first.click(timeout=5000)
            print("Successfully clicked continue")
        except Exception as e:
            print(f"Failed to click continue: {e}")
            
        page.screenshot(path="login_debug3.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    test()
