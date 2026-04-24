/**
 * Google Apps Script — Amazon Price Scraper Web App
 * 
 * Paste this into your Google Sheet's Apps Script editor.
 * Deploy as a Web App (Anyone can access) to get a free POST endpoint.
 * 
 * Sheet: https://docs.google.com/spreadsheets/d/19SO-QzFsk01snWF6-2R9ECkNYKu7ujne2mYgZripvLE
 */

var SHEET_NAME = "Sheet1";  // Change if your tab has a different name

var HEADERS = [
  "Barcode",
  "ASIN",
  "Product Name",
  "Price",
  "Currency",
  "Postal Code",
  "Amazon URL",
  "Date Scraped"
];

function doPost(e) {
  try {
    var sheet = SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheetByName(SHEET_NAME);

    if (!sheet) {
      return respond("error", "Sheet tab '" + SHEET_NAME + "' not found.");
    }

    // Auto-create header row if the sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.getRange(1, 1, 1, HEADERS.length)
           .setFontWeight("bold")
           .setBackground("#1a73e8")
           .setFontColor("#ffffff");
    }

    // Parse the JSON data sent by Python
    var data = JSON.parse(e.postData.contents);

    // Append the new product row
    sheet.appendRow([
      data.barcode     || "",
      data.asin        || "",
      data.name        || "",
      data.price       || "",
      data.currency    || "",
      data.postal_code || "",
      data.url         || "",
      data.date        || new Date().toISOString()
    ]);

    return respond("success", "Row added successfully.");

  } catch (err) {
    return respond("error", err.toString());
  }
}

// Helper: return a JSON response
function respond(status, message) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: status, message: message }))
    .setMimeType(ContentService.MimeType.JSON);
}
