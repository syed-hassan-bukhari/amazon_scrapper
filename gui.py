import threading
import time
import requests
import customtkinter as ctk
from tkinter import messagebox
from scraper import scrape_by_barcode, set_delivery_location
from sheets import save_to_sheet

# Setup Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AmazonScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Amazon Batch Price Scanner")
        self.geometry("650x650")
        self.resizable(False, False)

        # Session for maintaining cookies/location
        self.session = requests.Session()
        self.current_location = None
        self.is_scanning = False
        self.cancel_requested = False

        # ─── Title Label ───
        self.lbl_title = ctk.CTkLabel(
            self, text="📦 Amazon Batch Price Scanner", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.lbl_title.pack(pady=(20, 5))

        self.lbl_subtitle = ctk.CTkLabel(
            self, text="Paste multiple barcodes (one per line) • Free • Proxy-Free", text_color="gray"
        )
        self.lbl_subtitle.pack(pady=(0, 15))

        # ─── Input Frame ───
        self.frame_inputs = ctk.CTkFrame(self)
        self.frame_inputs.pack(pady=10, padx=20, fill="x")

        # ZIP Code
        self.lbl_zip = ctk.CTkLabel(self.frame_inputs, text="Postal / ZIP Code:")
        self.lbl_zip.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.ent_zip = ctk.CTkEntry(self.frame_inputs, placeholder_text="e.g. 10001", width=150)
        self.ent_zip.grid(row=1, column=0, padx=10, pady=(0, 15), sticky="nw")

        # Barcode Textbox (Multi-line)
        self.lbl_barcode = ctk.CTkLabel(self.frame_inputs, text="Barcodes (One per line):")
        self.lbl_barcode.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="w")
        
        self.txt_barcodes = ctk.CTkTextbox(self.frame_inputs, width=380, height=120)
        self.txt_barcodes.grid(row=1, column=1, padx=10, pady=(0, 15), sticky="ew")

        # ─── Scan Button ───
        # ─── Button Frame ───
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.pack(pady=10, padx=20, fill="x")

        # Scan Button
        self.btn_scan = ctk.CTkButton(
            self.frame_buttons, text="⚡ Start Batch Scan", height=40, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_scan, fg_color="#f59e0b", hover_color="#d97706", text_color="black"
        )
        self.btn_scan.pack(side="left", pady=0, padx=(0, 5), fill="x", expand=True)

        # Cancel Button
        self.btn_cancel = ctk.CTkButton(
            self.frame_buttons, text="❌ Cancel Scan", height=40, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.cancel_scan, fg_color="#ef4444", hover_color="#dc2626", text_color="white",
            state="disabled"
        )
        self.btn_cancel.pack(side="left", pady=0, padx=(5, 0), fill="x", expand=True)

        # ─── Progress Bar ───
        self.progress_bar = ctk.CTkProgressBar(self, height=8)
        self.progress_bar.pack(padx=20, fill="x")
        self.progress_bar.set(0)

        # ─── Result Frame ───
        self.frame_result = ctk.CTkFrame(self, fg_color="#1a2236")
        self.frame_result.pack(pady=15, padx=20, fill="both", expand=True)
        
        self.lbl_status = ctk.CTkLabel(self.frame_result, text="Ready to scan.", text_color="gray", font=ctk.CTkFont(size=13))
        self.lbl_status.pack(pady=10)

        self.lbl_product_name = ctk.CTkLabel(
            self.frame_result, text="—", font=ctk.CTkFont(size=14, weight="bold"), wraplength=550
        )
        self.lbl_product_name.pack(pady=(10, 5))

        self.lbl_price = ctk.CTkLabel(
            self.frame_result, text="—", font=ctk.CTkFont(size=36, weight="bold"), text_color="#10b981"
        )
        self.lbl_price.pack(pady=10)

    def start_scan(self):
        if self.is_scanning:
            return

        raw_text = self.txt_barcodes.get("1.0", "end-1c")
        # Split by newline and remove empty lines
        barcodes = [b.strip() for b in raw_text.split("\n") if b.strip()]
        postal_code = self.ent_zip.get().strip()

        if not barcodes:
            messagebox.showwarning("Warning", "Please enter at least one barcode.")
            return

        self.is_scanning = True
        self.cancel_requested = False
        self.btn_scan.configure(state="disabled", text="Scanning...")
        self.btn_cancel.configure(state="normal")
        self.progress_bar.set(0)
        self.lbl_product_name.configure(text="—")
        self.lbl_price.configure(text="—")

        # Run scraping in a background thread to prevent UI freezing
        thread = threading.Thread(target=self.run_batch_scrape, args=(barcodes, postal_code))
        thread.daemon = True
        thread.start()

    def cancel_scan(self):
        if self.is_scanning:
            self.cancel_requested = True
            self.update_status("Cancelling scan...", "#f59e0b")
            self.btn_cancel.configure(state="disabled")

    def run_batch_scrape(self, barcodes, postal_code):
        total = len(barcodes)
        success_count = 0

        try:
            # 1. Update location only if it changed
            if postal_code and postal_code != self.current_location:
                self.update_status(f"Setting location to {postal_code}...", "#f59e0b")
                set_delivery_location(self.session, postal_code)
                self.current_location = postal_code

            # Loop through each barcode
            for idx, barcode in enumerate(barcodes):
                self.update_status(f"[{idx+1}/{total}] Searching for {barcode}...", "#3b82f6")
                
                # Scrape Amazon
                product = scrape_by_barcode(barcode, self.session)

                if not product:
                    self.update_product_ui("Not Found", f"Barcode: {barcode}", "gray")
                else:
                    self.update_status(f"[{idx+1}/{total}] Saving {barcode} to Google Sheet...", "#f59e0b")
                    saved = save_to_sheet(product, postal_code=postal_code)
                    
                    price_text = f"{product.get('currency', '')}{product.get('price', '')}" if product.get('price') != 'N/A' else "Price Not Found"
                    name_text = f"{product.get('name', '')} (ASIN: {product.get('asin', '')})"
                    
                    if saved:
                        self.update_product_ui(price_text, name_text, "#10b981")
                        success_count += 1
                    else:
                        self.update_product_ui(price_text, f"FAILED TO SAVE: {name_text}", "#ef4444")

                # Update progress bar
                self.progress_bar.set((idx + 1) / total)

                # Wait between requests to avoid Amazon rate limits (except after the last one)
                if idx < total - 1:
                    self.update_status(f"[{idx+1}/{total}] Waiting 3 seconds to prevent bot detection...", "gray")
                    # Responsive sleep loop
                    for _ in range(30):
                        if self.cancel_requested:
                            break
                        time.sleep(0.1)

                if self.cancel_requested:
                    break

            # Finished
            if self.cancel_requested:
                self.update_status(f"Scan Cancelled. Successfully saved {success_count} items.", "#ef4444")
            else:
                self.update_status(f"Batch Complete! Successfully saved {success_count} out of {total} items.", "#10b981")

        except Exception as e:
            self.update_status(f"An error occurred: {str(e)}", "#ef4444")
            
        finally:
            self.is_scanning = False
            def reset_ui():
                self.btn_scan.configure(state="normal", text="⚡ Start Batch Scan")
                self.btn_cancel.configure(state="disabled")
            self.after(0, reset_ui)

    # Thread-safe UI update helpers
    def update_status(self, text, color):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def update_product_ui(self, price, name, price_color):
        self.after(0, lambda: self.lbl_price.configure(text=price, text_color=price_color))
        self.after(0, lambda: self.lbl_product_name.configure(text=name))

if __name__ == "__main__":
    app = AmazonScannerApp()
    app.mainloop()
