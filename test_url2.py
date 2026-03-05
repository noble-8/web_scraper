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
        
        email_input = page.locator("input[type='email'], input[name='email'], input[type='text']").locator("visible=true").first
        email_input.wait_for(state="visible", timeout=60000)
        email_input.fill(email)
        
        continue_btn = page.locator("input#continue, input[type='submit']").locator("visible=true").first
        continue_btn.click()
        
        password_input = page.locator("input[type='password'], input[name='password']").locator("visible=true").first
        password_input.wait_for(state="visible", timeout=60000)
        password_input.fill(password)
        
        submit_btn = page.locator("input#signInSubmit, input[type='submit']").locator("visible=true").first
        submit_btn.click()
        
        try:
            page.wait_for_url("**/order-history*", timeout=15000)
            print("Successfully logged in.")
        except Exception as e:
            print("Login took too long or encountered anti-bot measures (CAPTCHA/OTP).")
            print("Current URL:", page.url)
            page.screenshot(path="login_debug_after_submit.png", full_page=True)
            with open("login_debug_after_submit.html", "w") as f:
                f.write(page.content())
        
        browser.close()

if __name__ == "__main__":
    test()
