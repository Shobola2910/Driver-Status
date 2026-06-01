"""
setup_sheet.py
==============
Birinchi marta ishga tushiring: python setup_sheet.py

Google Sheets ni sozlaydi:
  - Sarlavha qatori (header) yozadi
  - Har bir ustun uchun kenglik belgilaydi
  - 1-qatorni freeze qiladi
  - Header ga ko'k fon va oq, qalin matn beradi
"""

import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = ["STATUS", "DRIVER NAME", "COMPANY NAME", "STATUS_KEY", "REASON / NOTES", "DATE"]

# Ustun kengliklari (pixel)
COLUMN_WIDTHS = [160, 200, 200, 120, 320, 160]


def setup():
    if not SHEET_ID:
        raise ValueError("SHEET_ID topilmadi! .env faylini tekshiring.")

    creds  = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).sheet1
    ss     = sheet.spreadsheet

    print("Header yozilmoqda...")
    sheet.clear()
    sheet.append_row(HEADERS, value_input_option="USER_ENTERED")

    sheet_id = sheet.id

    requests = []

    # ── 1. Freeze 1-qator ─────────────────────────────────────────────────────
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    })

    # ── 2. Header rangi (ko'k fon, oq qalin matn) ─────────────────────────────
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": len(HEADERS),
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.267, "green": 0.447, "blue": 0.769},
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "bold": True,
                        "fontSize": 11,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                }
            },
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
        }
    })

    # ── 3. Ustun kengliklari ───────────────────────────────────────────────────
    for col_idx, width in enumerate(COLUMN_WIDTHS):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })

    # ── 4. Barcha qatorlar balandligi ─────────────────────────────────────────
    requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 1,
            },
            "properties": {"pixelSize": 36},
            "fields": "pixelSize",
        }
    })

    # ── 5. STATUS_KEY ustunini yashirish (D ustuni) ───────────────────────────
    requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 3,
                "endIndex": 4,
            },
            "properties": {"hiddenByUser": True},
            "fields": "hiddenByUser",
        }
    })

    ss.batch_update({"requests": requests})

    print("OK: Google Sheets sozlandi!")
    print(f"Sheet ID: {SHEET_ID}")
    print(f"Ustunlar: {', '.join(HEADERS)}")
    print("1-qator freeze qilindi, STATUS_KEY ustuni yashirildi.")


if __name__ == "__main__":
    setup()
