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
        for sel in email_selectors:
            try:
                elem = page.locator(sel).locator("visible=true").first
                elem.wait_for(state="visible", timeout=5000)
                elem.fill(email)
                print(f"Successfully filled email using {sel}")
                break
            except Exception as e:
                print(f"Failed with {sel}: {e}")
                
        try:
            btn = page.locator("input#continue").locator("visible=true").first
            if btn.count() == 0:
                btn = page.locator("input[type='submit']").locator("visible=true").first
            btn.click()
            print("Successfully clicked continue")
        except Exception as e:
            print(f"Failed to click continue: {e}")
            
        page.screenshot(path="login_debug2.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    test()
