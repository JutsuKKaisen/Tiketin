import os
import time
import csv
import gspread
import qrcode
import random
import string
from PIL import Image
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from flask import Flask, request, jsonify, render_template, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

# Cấu hình Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Kết nối Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open(os.getenv("SHEET_NAME")).sheet1  # Cập nhật tên sheet

# Cache dữ liệu để tránh truy xuất Google Sheets liên tục
CACHE_DATA = {"records": [], "timestamp": 0}
CACHE_EXPIRY = 60  # Cache trong 60 giây

def get_cached_records():
    global CACHE_DATA
    current_time = time.time()
    
    # Nếu cache hết hạn, làm mới dữ liệu từ Google Sheets
    if current_time - CACHE_DATA["timestamp"] > CACHE_EXPIRY:
        CACHE_DATA["records"] = sheet.get_all_records()
        CACHE_DATA["timestamp"] = current_time

    return CACHE_DATA["records"]

# Tài khoản hệ thống
users = {
    user: {"password": os.getenv(f"{user.upper()}_PASSWORD"), "role": os.getenv(f"{user.upper()}_ROLE")}
    for user in os.getenv("USERS").split(",")
}

class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.role = role

@login_manager.user_loader
def load_user(username):
    user_data = users.get(username)
    if user_data:
        return User(username, user_data["role"])
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    """ Đăng nhập hệ thống """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user_data = users.get(username)
        if user_data and user_data["password"] == password:
            user = User(username, user_data["role"])
            login_user(user)

            # Kiểm tra nếu có `next` thì chuyển hướng đến đó
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))

        return "Sai tài khoản hoặc mật khẩu!", 403

    return render_template("login.html")

@app.route("/")
@login_required
def dashboard():
    """ Điều hướng theo phân quyền """
    if current_user.role == "admin":
        return render_template("admin.html", role="admin")
    else:
        return render_template("checkin.html", role="op")

@app.route("/logout")
@login_required
def logout():
    """ Đăng xuất hệ thống """
    logout_user()
    return redirect(url_for("login"))

@app.route("/view_tickets")
@login_required
def view_tickets():
    """ Hiển thị danh sách vé từ Google Sheets """
    if current_user.role != "admin":
        return "❌ Bạn không có quyền truy cập!", 403

    records = sheet.get_all_records()
    return render_template("view_tickets.html", records=records)

@app.route("/upload_csv", methods=["GET", "POST"])
@login_required
def upload_csv():
    """Admin tải lên file CSV để nhập dữ liệu vé, tạo mã QR, và lưu ảnh lên Google Drive"""
    if current_user.role != "admin":
        return jsonify({"error": "Bạn không có quyền upload file CSV!"}), 403

    if request.method == "GET":
        return render_template("upload_csv.html")

    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file trong request!"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename.endswith(".csv"):
        return jsonify({"error": "Chỉ chấp nhận file CSV!"}), 400

    try:
        # Đọc dữ liệu từ file CSV
        file_contents = file.read().decode("utf-8").splitlines()
        csv_reader = csv.reader(file_contents)

        # Kiểm tra header
        header = next(csv_reader, None)
        expected_columns = ["TEN", "MSSV", "LOP", "MAIL", "SDT"]
        if header != expected_columns:
            return jsonify({"error": f"Định dạng CSV không đúng! Cần các cột: {expected_columns}"}), 400

        csv_data = list(csv_reader)

        # Khởi tạo Google Drive
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)
        DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")  # Cập nhật ID thực tế

        qr_dir = "output"
        os.makedirs(qr_dir, exist_ok=True)

        # Cấu hình vị trí QR trên phôi
        TEMPLATE_PATH = os.getenv("TEMPLATE_PATH")  # Đường dẫn đến ảnh phôi
        OUTPUT_DIR = qr_dir
        QR_SIZE = (300, 300)  # Kích thước QR
        QR_POSITION = (1300, 200)  # Vị trí QR trên phôi

        # Lấy dữ liệu từ Google Sheet
        sheet = client.open("Copy_of_database_gculaw_tiketin").sheet1
        records = sheet.get_all_values()
        max_row = sheet.row_count
        used_rows = {idx + 1 for idx, row in enumerate(records) if len(row) > 0 and row[0].strip()}
        empty_rows = [i for i in range(2, max_row + 1) if i not in used_rows]

        if len(empty_rows) < len(csv_data):
            return jsonify({"error": "Không đủ hàng trống trong Google Sheet!"}), 400

        updates = []
        for i, row in enumerate(csv_data):
            ten, mssv, lop, mail, sdt = row
            row_index = empty_rows[i]

            # 📌 Sinh mã CODE theo quy tắc mới (10 ký tự chữ + số)
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

            # Tạo ảnh QR gắn vào phôi
            qr = qrcode.make(code)
            qr = qr.resize(QR_SIZE)
            template = Image.open(TEMPLATE_PATH)
            template.paste(qr, QR_POSITION)

            ticket_path = os.path.join(OUTPUT_DIR, f"{code}.png")
            template.save(ticket_path)

            # Upload lên Google Drive
            gfile = drive.CreateFile({
                'title': f"{code}.png",
                'parents': [{'id': DRIVE_FOLDER_ID}]
            })
            gfile.SetContentFile(ticket_path)
            gfile.Upload()
            drive_link = gfile['alternateLink']

            # Ghi vào sheet các cột: A-G = CODE, TEN, MSSV, LOP, MAIL, SDT, LINK
            updates.append({
                'range': f"A{row_index}:G{row_index}",
                'values': [[code, ten, mssv, lop, mail, sdt, drive_link]]
            })

        response = sheet.batch_update(updates)
        print("Ghi sheet thành công:", response)

        return jsonify({"message": "✅ Đã tải lên CSV, tạo mã QR và lưu vé thành công!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Chi tiết lỗi:", type(e), e)
        return jsonify({"error": f"Lỗi xử lý CSV: {str(e)}"}), 500



@app.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    """ OP và Admin có thể check-in vé """
    if request.method == "GET":
        return render_template("checkin.html", role=current_user.role)

    try:
        data = request.json
        code = data.get("code", "").strip()

        if not code:
            return jsonify({"error": "Mã QR không hợp lệ!"}), 400

        # Chuyển danh sách thành từ điển để truy xuất nhanh hơn
        records = get_cached_records()
        record_dict = {r["CODE"]: r for r in records}

        if code not in record_dict:
            return jsonify({"error": f"Không tìm thấy mã CODE `{code}` trong hệ thống!"}), 404

        row_data = record_dict[code]
        row_index = records.index(row_data) + 2  # Hàng trong Google Sheets

        # Nếu là OP, cập nhật trạng thái check-in
        if current_user.role == "op":
            sheet.update(values=[["Đã Check-in"]], range_name=f"G{row_index}")

        return jsonify({
            "message": "Check-in thành công!" if current_user.role == "op" else "Thông tin vé",
            "ten": row_data["TEN"],
            "mssv": row_data["MSSV"],
            "lop": row_data["LOP"],
            "mail": row_data["MAIL"],
            "sdt": row_data["SDT"],
            "trangthai": "Đã Check-in" if current_user.role == "op" else row_data.get("trangthai", "Chưa check-in")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/send_emails", methods=["GET", "POST"])
@login_required
def send_emails():
    """Hiển thị danh sách email hợp lệ và thực hiện gửi email khi xác nhận"""
    if current_user.role != "admin":
        return jsonify({"error": "Bạn không có quyền gửi email!"}), 403

    from concurrent.futures import ThreadPoolExecutor
    import queue

    # 🔹 Cấu hình
    sheet = client.open("Copy_of_database_gculaw_tiketin").sheet1
    rows = sheet.get_all_values()
    header = rows[0]
    data_rows = rows[1:]
    output_dir = "output"
    email_template_path = "email_template.html"
    max_threads = 5
    retry_count = 1

    # 🔹 Xác định cột
    header_map = {h.strip(): i for i, h in enumerate(header)}
    email_col = header_map.get("MAIL")
    code_col = header_map.get("CODE")
    name_col = header_map.get("TEN")
    mail_status_col = header_map.get("TRANG_THAI_VE")

    if email_col is None or code_col is None or mail_status_col is None or name_col is None:
        return jsonify({"error": "Không tìm thấy đủ cột CODE, TEN, MAIL hoặc MAIL_STATUS trong Google Sheet"}), 400

    # 🔹 Lọc dòng đủ điều kiện gửi
    valid_rows = []
    for idx, row in enumerate(data_rows):
        row_index = idx + 2
        if len(row) > max(email_col, code_col, mail_status_col, name_col):
            email = row[email_col].strip()
            code = row[code_col].strip()
            name = row[name_col].strip()
            status = row[mail_status_col].strip().lower()
            img_path = os.path.join(output_dir, f"{code}.png")
            if email and code and status != "đã gửi" and os.path.exists(img_path):
                valid_rows.append({"row": row_index, "email": email, "code": code, "name": name})

    if request.method == "GET":
        return render_template("send_emails.html", emails=valid_rows)

    if not valid_rows:
        return jsonify({"error": "Không có dòng nào đủ điều kiện gửi email!"}), 400

    try:
        with open(email_template_path, "r", encoding="utf-8") as f:
            email_content = f.read()

        email_queue = queue.Queue()
        for item in valid_rows:
            email_queue.put((item["row"], item["email"], item["code"]))

        def send_email(row_index, to_email, qr_code):
            for attempt in range(1, retry_count + 1):
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as smtp_server:
                        smtp_server.starttls()
                        smtp_server.login("clbguitardhluat@gmail.com", "muxf iqic tixv xqoq")

                        msg = MIMEMultipart()
                        msg["From"] = "clbguitardhluat@gmail.com"
                        msg["To"] = to_email
                        msg["Subject"] = "[GCULAW] - XÁC NHẬN ĐĂNG KÝ THAM DỰ ĐÊM NHẠC"

                        html = f"<html><body>{email_content}<br><br></body></html>"
                        msg.attach(MIMEText(html, "html"))

                        qr_path = os.path.join(output_dir, f"{qr_code}.png")
                        with open(qr_path, "rb") as f:
                            img = MIMEImage(f.read())
                            img.add_header("Content-ID", "<qr_image>")
                            msg.attach(img)

                        smtp_server.sendmail("clbguitardhluat@gmail.com", to_email, msg.as_string())
                        print(f"✅ Gửi email đến {to_email}")

                        # Cập nhật trạng thái trong Sheet
                        sheet.update(f"I{row_index}", [["Đã gửi"]])
                        return
                except Exception as e:
                    print(f"❌ Thử lại ({attempt}) gửi {to_email}: {e}")
                    time.sleep(1)

        def worker():
            while not email_queue.empty():
                try:
                    row_index, email, code = email_queue.get_nowait()
                    send_email(row_index, email, code)
                except queue.Empty:
                    break
                finally:
                    email_queue.task_done()

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for _ in range(max_threads):
                executor.submit(worker)

        return jsonify({"message": f"✅ Đã gửi email cho {len(valid_rows)} người!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi gửi email: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)