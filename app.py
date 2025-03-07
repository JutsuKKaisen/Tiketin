import os
from flask import Flask, request, jsonify, session, render_template
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials


app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("key.env")
app.secret_key = "a113649be1203ff3702f3e06fa91178718cf1551f6c88b1eb677988f6e9168cd"

# Kết nối Google Sheets
def connect_to_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    SHEET_NAME = "database_gculaw_tiketin"  # Đổi thành tên bảng của bạn
    
    try:
        sheet = client.open(SHEET_NAME).sheet1  # Chọn sheet đầu tiên
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        print("Lỗi: Không tìm thấy bảng tính!")
        return None

sheet = connect_to_sheets()
if sheet is None:
    raise ValueError("Không thể kết nối Google Sheets!")

# Trang chủ
@app.route('/')
def index():
    return render_template("index.html")

#API quét QR
@app.route("/scan", methods=["POST"])
def scan():
    """ Xử lý quét mã QR, lưu `CODE` vào session nếu tồn tại trong database """
    try:
        data = request.json
        code = data.get("code", "").strip()

        if not code:
            return jsonify({"error": "Mã QR không hợp lệ!"}), 400

        # 🔍 Tìm mã QR trong Google Sheets
        records = sheet.get_all_records()
        found_record = next((row for row in records if row["CODE"] == code), None)

        if found_record:
            session["last_scanned_code"] = code  # 🔥 Lưu mã vào session
            return jsonify({"status": "found", "code": code, "data": found_record})
        else:
            return jsonify({"status": "not_found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#API update dữ liệu
@app.route("/update", methods=["POST"])
def update():
    """ Cập nhật thông tin vào Google Sheets sau khi quét QR """
    try:
        if "last_scanned_code" not in session:
            return jsonify({"error": "Chưa có mã QR nào được quét!"}), 400
        code = session["last_scanned_code"]  # 🔥 Lấy mã QR từ session

        data = request.form.to_dict()

        # 🔍 Kiểm tra đủ các trường dữ liệu
        required_fields = ["ten", "mssv", "mail", "sdt", "phuong_thuc_thanh_toan", "trang_thai"]
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({"error": f"Thiếu trường `{field}`!"}), 400

        # 🔍 Tìm hàng chứa mã QR đã quét
        records = sheet.get_all_records()
        row_index = next((i + 2 for i, row in enumerate(records) if row["CODE"] == code), None)
        if row_index is None:
            return jsonify({"error": f"Không tìm thấy mã CODE `{code}` trong Google Sheets!"}), 404

        # 🔄 Cập nhật dữ liệu vào Google Sheets
        sheet.update(f"B{row_index}:G{row_index}", [[
            data["ten"], data["mssv"], data["mail"], data["sdt"], 
            data["phuong_thuc_thanh_toan"], data["trang_thai"]
        ]])

        return jsonify({"message": "Cập nhật thành công!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/checkin", methods=["POST"])
def checkin():
    """ Cập nhật trạng thái "Đã check in" khi bấm nút Check-in """
    try:
        data = request.json
        code = data.get("code", "").strip()

        if not code:
            return jsonify({"error": "Mã QR không hợp lệ!"}), 400

        # 🔍 Tìm hàng chứa mã QR
        records = sheet.get_all_records()
        row_index = next((i + 2 for i, row in enumerate(records) if row["CODE"] == code), None)

        if row_index is None:
            return jsonify({"error": f"Không tìm thấy mã CODE `{code}` trong Google Sheets!"}), 404

        # ✅ Cập nhật trạng thái thành "Đã check in"
        sheet.update(f"G{row_index}", [["đã check in"]])

        return jsonify({"message": "Check-in thành công!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)