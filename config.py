# ─────────────────────────────────────────────
#  Amazon Barcode Price Scraper — Configuration
# ─────────────────────────────────────────────

# ── Google Sheets (via Apps Script Web App — NO credentials file needed) ──────
# Paste your deployed Apps Script Web App URL here.
# See README.md → "Setup" for the 2-minute steps to get this URL.
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOjggDWjuLQr8SUVf3ad8i77C7-L9VLBpKYZ0EBnJqdosRIlReBapvNywUtJd0zXUY/exec"

# Amazon base URL (change to .co.uk, .de, etc. for other regions)
AMAZON_BASE_URL = "https://www.amazon.com"

# Delay between requests (seconds) to avoid being flagged as a bot
REQUEST_DELAY = 2

# Max retries for failed requests
MAX_RETRIES = 3
