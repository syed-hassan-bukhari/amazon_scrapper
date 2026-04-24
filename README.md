# Amazon Barcode → Price → Google Sheets

Scrape a product's price from Amazon using its barcode and save it to your Google Sheet — **100% free, no paid API**.

---

## Features
- 🔍 Look up any product by **UPC / EAN / ISBN barcode**
- 🏷 Extracts **ASIN**, product name, and price from Amazon
- 📊 Saves directly to your **Google Sheet**
- 🔄 Retry logic + rotating User-Agents to handle Amazon's bot detection
- ⌨️ Works interactively OR with command-line arguments

---

## Columns Saved to Google Sheet

| Barcode | ASIN | Product Name | Price | Currency | Amazon URL | Date Scraped |
|---------|------|--------------|-------|----------|------------|--------------|
| 0194253716085 | B09G9FPHY6 | Apple AirPods... | 179.99 | $ | https://... | 2024-04-24 20:14:00 |

---

## Setup (One-Time — ~5 Minutes)

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

### Step 2 — Create a Free Google Service Account

This is a free Google feature that lets a script write to your sheet.

1. Go to **[Google Cloud Console](https://console.cloud.google.com)**
2. Click **"Select a project"** → **"New Project"** → name it anything → **Create**
3. In the left sidebar go to **APIs & Services → Library**
4. Search for **"Google Sheets API"** → click it → click **Enable**
5. Search for **"Google Drive API"** → click it → click **Enable**
6. Go to **APIs & Services → Credentials**
7. Click **"+ Create Credentials"** → choose **"Service account"**
8. Fill in a name (e.g. `amazon-scraper`) → click **Create and Continue** → **Done**
9. Click on the service account you just created
10. Go to the **Keys** tab → **Add Key → Create new key → JSON** → **Create**
11. A `.json` file downloads — **rename it to `credentials.json`** and place it in this project folder

---

### Step 3 — Share Your Google Sheet with the Service Account

1. Open the downloaded `credentials.json` file
2. Find the `"client_email"` field — it looks like:
   ```
   amazon-scraper@your-project.iam.gserviceaccount.com
   ```
3. Open your Google Sheet: https://docs.google.com/spreadsheets/d/19SO-QzFsk01snWF6-2R9ECkNYKu7ujne2mYgZripvLE
4. Click **Share** (top-right)
5. Paste the service account email → set role to **Editor** → click **Send**

---

### Step 4 — Run the Scraper

**Interactive mode** (prompts you for barcodes):
```bash
python main.py
```

**Single barcode:**
```bash
python main.py 0194253716085
```

**Multiple barcodes at once:**
```bash
python main.py 0194253716085 9780132350884 0012345678905
```

---

## Project Structure

```
amazon_scrapper/
├── main.py           # Entry point (run this)
├── scraper.py        # Amazon scraping logic
├── sheets.py         # Google Sheets writer
├── config.py         # Settings (sheet ID, etc.)
├── requirements.txt  # Dependencies
├── credentials.json  # ← YOU ADD THIS (Service Account key)
└── README.md
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `credentials.json not found` | Download from Google Cloud and place in this folder |
| `403 Forbidden` on Google Sheets | Share the sheet with your service account email |
| Amazon returns CAPTCHA | Wait a few minutes and try again. Amazon rate-limits scrapers. |
| Price shows `N/A` | The product page layout may have changed. Open an issue. |
| Product not found | Try the full UPC/EAN. Some barcodes map to multiple products. |
