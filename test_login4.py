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
        
        email_selectors = ["input[name='email']", "input[type='email']", "input[type='text']"]
        success = False
        for sel in email_selectors:
            try:
                elem = page.locator(sel).locator("visible=true").first
                elem.wait_for(state="visible", timeout=5000)
                elem.fill(email)
                print(f"Successfully filled email using {sel} with visible=true")
                success = True
                break
            except Exception as e:
                print(f"Failed with {sel}: {e}")
                
        if not success:
            print("Failed to fill email completely.")
                
        try:
            elem = page.locator("input#continue, input[type='submit']").locator("visible=true").first
            elem.click(timeout=5000)
            print("Successfully clicked continue")
        except Exception as e:
            print(f"Failed to click continue: {e}")
            
        page.screenshot(path="login_debug4.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    test()
