# Amazon Mobile Order Scraper

This is a Take-Home Assignment to build a scraper that logs into an Amazon account, navigates to the order history using a **mobile user agent**, and outputs the transactions array in the exact schema specified by the Knot TransactionLink API.

## Requirements Checklist
- [x] Programmatic Authentication
- [x] **Mobile user agent** emulation
- [x] Extraction of required fields from order history
- [x] Output schema matching instructions precisely
- [x] `README.md` included
- [x] CLI arguments added (`--months`, `--output`) (Bonus)
- [x] Handles Pagination (Bonus)

## Approach & Justification
I chose **Python with Playwright** (Headless Browser) as the scraping solution over raw HTTP requests. 
**Justification:**
1. **Dynamic Content and Anti-Bot:** Amazon's front-end logic heavily relies on JS execution to complete forms and pass CSRF/anti-bot checks. Raw HTTP requests would quickly get flagged or stuck behind captchas. Playwright lets us mimic real human navigation, run JavaScript, and even bypass simple superficial checks by executing the real frontend code.
2. **Mobile User Agent Simulation:** Playwright acts as a full browser engine where we can instantly adopt any popular mobile device's User-Agent, viewport width, and screen parameters simply by calling `devices['iPhone 13']` (or another modern mobile).
3. **Resilience:** Playwright's `wait_for_selector` makes handling Amazon's staggered network loads significantly easier than raw static parsing (like `beautifulsoup4` paired with `requests`).

## Setup Instructions

1. **Install Python 3.9+** (if not already installed).
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **Provide Credentials:**
   Create a `.env` file in the root directory (or export the variables) containing your test credentials:
   ```env
   AMAZON_EMAIL="your_test_email@example.com"
   AMAZON_PASSWORD="your_test_password"
   ```
4. **Run the Scraper:**
   Because Amazon has extremely aggressive bot detection (Captchas, "Dogs of Amazon" pages, and OTP login checks), it is **highly recommended** to run the scraper in "headful" mode (visible browser) using your existing Brave/Chrome profile. This allows you to manually solve any Captchas so the scraper can continue.
   
   *Ensure all Brave windows are fully closed before running this command to avoid profile locks.*
   ```bash
   python scrape.py --months 1 --output transactions.json --use-brave --headful
   ```
   
   If you encounter a CAPTCHA or security checkpoint, the script will wait, giving you time to solve it in the visible window. Once solved, it will automatically resume scraping and populate `transactions.json`.
## Assumptions & Limitations
- **Anti-Bot Protections (Captchas/OTPs):** Amazon actively defends against scraping. If a CAPTCHA or Two-Factor Authentication (OTP) prompt appears during login or navigation, the scraper will wait (up to 60 seconds). Because of this, exposing the browser UI (`--headful`) and leveraging an existing browser profile (`--use-brave`) is implemented to allow manual human intervention to bypass these checkpoints. In a production environment, you would hook this into a service like 2Captcha or use resident proxies.
- **Mobile Selectors:** DOM layouts on Amazon vary slightly via A/B testing and account types. The script targets the most widely seen classes for the mobile view (`.a-box`, `.a-color-price`, IDs prefixing `order-`, etc.). However, Amazon's DOM is highly volatile. Missing data fields have fallback `null` or empty strings per standard guidelines to prevent abrupt crashes.
- **Null Fields Justification:** As per the API guidelines, if data cannot be extracted reliably, it defaults to `null`.
  - **Shipping Address:** Amazon often obfuscates or completely hides the full recipient address string on the "Order Details" page for certain mobile accounts for privacy (or places it behind a secondary "View Invoice" link). The scraper parses it via regex if it is rendered on the page DOM, but defaults `line1`, `city`, `region` etc. to `null` if Amazon blocks it from viewing.
  - **Seller Info:** If the item does not explicitly contain a rendered "Sold by:" tag on the top-level order details DOM (frequently omitted for native Amazon products or bundled items), `seller.name` gracefully defaults to `null`. 
- **Card Information:** Exact raw payment transaction details on Amazon are often visually redacted down to just the last 4 digits (e.g., "Visa ending in 1234"). The sub-level fields `last_four`, `brand`, and `type` extract this correctly, but exact amounts tied to split-card payments might be partially inferred from the total if exactly one card was used.
- **Digital Orders:** Handled gracefully. If an order lacks a physical delivery location (e.g., Kindle e-book, Prime Video rental), the `shipping` block resolves to `null` to comply with realistic constraints, or empty if it's partly physical.

## Output Details
When completed, `transactions.json` will contain a JSON array containing exact Node/ID schema mappings, compliant with the Knot TransactionLink expected payload structure, utilizing UUID4 generation.
