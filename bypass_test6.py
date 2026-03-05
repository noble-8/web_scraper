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
        
        # Wait up to 30 seconds to bypass potential challenges
        for i in range(15):
            page.wait_for_timeout(2000)
            print(f"Checking URL {i}... URL = {page.url}")
            
            # Check for OTP page
            if "cvf/request" in page.url or "claim" in page.url or "challenge" in page.url:
                try:
                    # Check for "Send OTP" button
                    send_btn = page.locator("input#continue, input[type='submit'][name='cvf_action'][value*='Send']").locator("visible=true").first
                    if send_btn.count() > 0:
                        print("Found OTP Send button, submitting...")
                        send_btn.click()
                        page.wait_for_timeout(3000)
                except:
                    pass
                    
                # Look for the actual OTP input box and read from env if provided
                try:
                    otp_input = page.locator("input[type='text'][name='code'], input[name='otpCode']").locator("visible=true").first
                    if otp_input.count() > 0:
                        manual_otp = os.getenv("AMAZON_OTP")
                        if manual_otp:
                            print(f"Found OTP Box. Filling with {manual_otp} and submitting...")
                            otp_input.fill(manual_otp)
                            otp_submit = page.locator("input#a-autoid-0-announce, input.a-button-input[type='submit']").locator("visible=true").first
                            otp_submit.click()
                            page.wait_for_timeout(5000)
                        else:
                            print("Found OTP Box but no AMAZON_OTP found in environment variables.")
                except:
                    pass

            if "order-history" in page.url.lower():
                print("Successfully logged in.")
                page.screenshot(path="success_orders.png", full_page=True)
                with open("success_orders.html", "w") as f:
                    f.write(page.content())
                break
        
        browser.close()

if __name__ == "__main__":
    test()
