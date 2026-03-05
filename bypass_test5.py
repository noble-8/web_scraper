import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time
import json
import urllib.parse

load_dotenv()

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"], headless=True)
        iphone = p.devices['iPhone 13'].copy()
        iphone.pop('default_browser_type', None)
        context = browser.new_context(**iphone)
        page = context.new_page()

        # Add stealth script
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        page.goto("https://www.amazon.com/gp/css/order-history?ref_=nav_AccountFlyout_orders", wait_until="domcontentloaded")
        
        email = os.getenv("AMAZON_EMAIL")
        password = os.getenv("AMAZON_PASSWORD")
        
        email_input = page.locator("input[type='email'], input[name='email'], input[type='text']").locator("visible=true").first
        email_input.wait_for(state="visible", timeout=60000)
        time.sleep(2)
        email_input.fill(email)
        time.sleep(1)
        
        continue_btn = page.locator("input#continue, input[type='submit']").locator("visible=true").first
        continue_btn.click()
        time.sleep(3)
        
        password_input = page.locator("input[type='password'], input[name='password']").locator("visible=true").first
        password_input.wait_for(state="visible", timeout=60000)
        password_input.fill(password)
        time.sleep(2)
        
        submit_btn = page.locator("input#signInSubmit, input[type='submit']").locator("visible=true").first
        submit_btn.click()
        
        try:
            page.wait_for_url("**/order-history*", timeout=20000) # Increased timeout
            print("Successfully logged in.")
            
            # Scrape basic summary of what's there to show it worked
            page.screenshot(path="success_orders.png", full_page=True)
            with open("success_orders.html", "w") as f:
                f.write(page.content())
        except Exception as e:
            print("Login took too long or encountered anti-bot measures (CAPTCHA/OTP).")
            print("Current URL:", page.url)
            page.screenshot(path="login_debug_after_submit_stealth.png", full_page=True)
            
            # Check if this is the "important message" OTP page
            try:
                # Often it's an email/SMS OTP page where we have to click "Send OTP"
                send_otp_btn = page.locator("input#continue, input[type='submit'][value*='Send']").locator("visible=true").first
                if send_otp_btn.count() > 0:
                    print("Found a 'Send OTP' button, clicking...")
                    send_otp_btn.click()
                    page.screenshot(path="login_debug_otp_sent.png", full_page=True)
                    print("Now blocked waiting for OTP code input...")
            except:
                pass
            
        browser.close()

if __name__ == "__main__":
    test()
