import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="webapp", static_url_path="")
CORS(app)

SHEET_ID = os.getenv("SHEET_ID")
PORT = int(os.getenv("PORT", 5000))

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

STATUS_CONFIG = {
    "GOOD":     {"emoji": "\U0001f7e2", "color": (183, 225, 205)},
    "MONITOR":  {"emoji": "\U0001f7e1", "color": (255, 242, 204)},
    "RED FLAG": {"emoji": "\U0001f534", "color": (255, 199, 206)},
}


def get_sheet():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("webapp", "index.html")


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/drivers", methods=["GET"])
def api_get_drivers():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()

        company_filter = request.args.get("company", "").strip()
        sort_by = request.args.get("sort", "newest")
        status_filter = request.args.get("status", "").strip()

        if company_filter:
            rows = [r for r in rows if r.get("COMPANY NAME", "").strip().lower() == company_filter.lower()]
        if status_filter and status_filter != "ALL":
            rows = [r for r in rows if r.get("STATUS_KEY", "") == status_filter]

        if sort_by == "az":
            rows.sort(key=lambda x: x.get("DRIVER NAME", "").lower())
        elif sort_by == "za":
            rows.sort(key=lambda x: x.get("DRIVER NAME", "").lower(), reverse=True)
        else:  # newest
            rows = list(reversed(rows))

        return jsonify({"success": True, "data": rows, "total": len(rows)})
    except Exception as e:
        logger.error(f"get_drivers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/companies", methods=["GET"])
def api_get_companies():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        companies = sorted(set(
            r.get("COMPANY NAME", "").strip()
            for r in rows if r.get("COMPANY NAME", "").strip()
        ))
        return jsonify({"success": True, "data": companies})
    except Exception as e:
        logger.error(f"get_companies: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        stats = {"GOOD": 0, "MONITOR": 0, "RED FLAG": 0, "total": len(rows)}
        for r in rows:
            key = r.get("STATUS_KEY", "")
            if key in stats:
                stats[key] += 1
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error(f"get_stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/drivers", methods=["POST"])
def api_add_driver():
    try:
        data = request.json or {}
        company    = data.get("company", "").strip()
        name       = data.get("name", "").strip()
        status_key = data.get("status", "GOOD")
        reason     = data.get("reason", "").strip()

        if not all([company, name, reason]):
            return jsonify({"success": False, "error": "Barcha maydonlar to'ldirilishi shart"}), 400
        if status_key not in STATUS_CONFIG:
            return jsonify({"success": False, "error": "Noto'g'ri status"}), 400

        sheet = get_sheet()
        cfg = STATUS_CONFIG[status_key]
        status_display = f"{cfg['emoji']} {status_key}"
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        row = [status_display, name, company, status_key, reason, date_str]
        sheet.append_row(row, value_input_option="USER_ENTERED")

        last_row = len(sheet.get_all_values())
        r, g, b = cfg["color"]
        sheet.spreadsheet.batch_update({"requests": [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": last_row - 1,
                    "endRowIndex": last_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": 6,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": r / 255, "green": g / 255, "blue": b / 255},
                        "textFormat": {"bold": status_key == "RED FLAG"},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        }]})

        return jsonify({"success": True, "message": "Driver muvaffaqiyatli qo'shildi"})
    except Exception as e:
        logger.error(f"add_driver: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
