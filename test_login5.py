import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        iphone = p.devices['iPhone 13'].copy()
        iphone.pop('default_browser_type', None)
        context = browser.new_context(**iphone)
        page = context.new_page()
        page.goto("https://www.amazon.com/gp/css/order-history?ref_=nav_AccountFlyout_orders", wait_until="domcontentloaded")
        
        email = os.getenv("AMAZON_EMAIL")
        password = os.getenv("AMAZON_PASSWORD")
        
        # Email step
        email_input = page.locator("input[type='email'], input[name='email'], input[type='text']").locator("visible=true").first
        email_input.wait_for(state="visible", timeout=60000)
        email_input.fill(email)
        
        continue_btn = page.locator("input#continue, input[type='submit']").locator("visible=true").first
        continue_btn.click()
        
        print("Clicked continue on email.")
        
        # Password step
        password_input = page.locator("input[type='password'], input[name='password']").locator("visible=true").first
        password_input.wait_for(state="visible", timeout=60000)
        password_input.fill(password)
        
        print("Filled password.")
        page.screenshot(path="login_debug_password.png", full_page=True)
        
        submit_btn = page.locator("input#signInSubmit, input[type='submit']").locator("visible=true").first
        submit_btn.click()
        
        print("Successfully clicked submit!")
        
        browser.close()

if __name__ == "__main__":
    test()
