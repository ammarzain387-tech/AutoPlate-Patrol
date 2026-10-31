import hashlib
import random
import smtplib
import sqlite3
from email.mime.text import MIMEText
import cv2
import easyocr
import numpy as np
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="AutoPlate Patrol — ANPR Command & Security System",
    page_icon="🚔",
    layout="wide",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        background-color: #0b1d3a;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #f1c40f;
        font-size: 26px;
        font-weight: bold;
        margin: 0;
        letter-spacing: 1px;
    }
    .main-header h3 {
        color: #ecf0f1;
        font-size: 15px;
        margin-top: 5px;
        font-weight: 300;
    }
    .stButton>button {
        background-color: #1b365d;
        color: white;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def send_otp_email(target_email, otp_code):
    sender_email = st.secrets.get("GMAIL_USER", "noreply.autoplate@gmail.com")
    sender_pass = st.secrets.get("GMAIL_PASS", "")

    msg = MIMEText(
        f"Your AutoPlate Patrol password reset OTP code is: {otp_code}\n\nDo not share this code with anyone."
    )
    msg["Subject"] = "AutoPlate Patrol — Security Password Reset OTP"
    msg["From"] = sender_email
    msg["To"] = target_email

    try:
        if sender_pass:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, target_email, msg.as_string())
            server.quit()
            return True, "OTP successfully sent to your registered Gmail!"
        else:
            return (
                True,
                f"DEBUG MODE: OTP Code generated is `{otp_code}`.",
            )
    except Exception as e:
        return False, f"Email delivery failed: {str(e)}"


def get_db_connection():
    return sqlite3.connect("stolen_vehicles.db", check_same_thread=False)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stolen_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            vehicle_model TEXT,
            vehicle_color TEXT,
            engine_number TEXT,
            chassis_number TEXT,
            owner_name TEXT,
            fir_number TEXT,
            status TEXT DEFAULT 'WANTED'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            belt_number TEXT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'STAFF'
        )
        """
    )

    cursor.execute("SELECT * FROM users WHERE role = 'ADMIN'")
    if not cursor.fetchone():
        admin_pass = hash_password("Admin@123")
        cursor.execute(
            """
            INSERT INTO users (full_name, belt_number, email, username, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "System Administrator",
                "ADM-001",
                "admin@autoplate.com",
                "admin",
                admin_pass,
                "ADMIN",
            ),
        )

    conn.commit()
    conn.close()


init_db()


@st.cache_resource
def load_ocr():
    return easyocr.Reader(["en"])


reader = load_ocr()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.full_name = ""

if "reset_otp" not in st.session_state:
    st.session_state.reset_otp = None
    st.session_state.reset_user = None

st.markdown(
    """
    <div class="main-header">
        <h1>AUTOPLATE PATROL — ANPR COMMAND CENTER</h1>
        <h3>AUTOMATED STOLEN & WANTED VEHICLE RECOGNITION SYSTEM</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
    st.sidebar.markdown("## 🔐 Admin Access Portal")
    st.sidebar.caption("Restricted area for System Administrators")
    admin_u = st.sidebar.text_input("Admin Username", key="admin_u_input")
    admin_p = st.sidebar.text_input(
        "Admin Password", type="password", key="admin_p_input"
    )

    if st.sidebar.button("Login as Admin"):
        if admin_u and admin_p:
            conn = get_db_connection()
            cursor = conn.cursor()
            hashed = hash_password(admin_p)
            cursor.execute(
                "SELECT full_name, role FROM users WHERE username = ? AND password = ? AND role = 'ADMIN'",
                (admin_u.strip(), hashed),
            )
            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state.logged_in = True
                st.session_state.full_name = user[0]
                st.session_state.role = user[1]
                st.session_state.username = admin_u
                st.sidebar.success(f"Admin Logged In: {user[0]}")
                st.rerun()
            else:
                st.sidebar.error("Invalid Admin credentials or unauthorized.")
        else:
            st.sidebar.warning("Enter Admin username & password.")

    st.sidebar.markdown("---")

    tab_staff_login, tab_forgot = st.tabs(
        ["👮 Duty Officer Login", "🔑 Forgot / Reset Password"]
    )

    with tab_staff_login:
        st.subheader("👮 Checkpost Duty Officer Login")
        col_login, col_info = st.columns([1, 1])

        with col_login:
            login_user = st.text_input("Officer Username", key="staff_u_input")
            login_pass = st.text_input(
                "Password", type="password", key="staff_p_input"
            )
            if st.button("Login to Checkpost Portal"):
                if login_user and login_pass:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    hashed = hash_password(login_pass)
                    cursor.execute(
                        "SELECT full_name, role FROM users WHERE username = ? AND password = ?",
                        (login_user.strip(), hashed),
                    )
                    user = cursor.fetchone()
                    conn.close()

                    if user:
                        st.session_state.logged_in = True
                        st.session_state.full_name = user[0]
                        st.session_state.role = user[1]
                        st.session_state.username = login_user
                        st.success(f"Welcome Officer, {user[0]} ({user[1]})!")
                        st.rerun()
                    else:
                        st.error("Invalid Officer Username or Password.")
                else:
                    st.warning("Please enter username and password.")

        with col_info:
            st.info(
                """
                **Duty Officer Access:**
                - Standard credentials assigned by System Admin.
                - For password issues, use the **Forgot / Reset Password** tab.
                """
            )

    with tab_forgot:
        st.subheader("🔑 Password Recovery via Registered Gmail")
        reset_username = st.text_input("Enter Registered Username or Email")

        if st.button("Send Recovery OTP"):
            if reset_username:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT email, username FROM users WHERE username = ? OR email = ?",
                    (reset_username.strip(), reset_username.strip()),
                )
                user_match = cursor.fetchone()
                conn.close()

                if user_match:
                    generated_otp = str(random.randint(100000, 999999))
                    st.session_state.reset_otp = generated_otp
                    st.session_state.reset_user = user_match[1]

                    success, msg = send_otp_email(
                        user_match[0], generated_otp
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("No account found with this Username/Email.")
            else:
                st.warning("Please enter your Username or Email.")

        if st.session_state.reset_otp:
            st.markdown("---")
            st.subheader("VERIFY OTP & SET NEW PASSWORD")
            input_otp = st.text_input("Enter 6-Digit OTP")
            new_pass = st.text_input("Enter New Password", type="password")

            if st.button("Update Password"):
                if (
                    input_otp == st.session_state.reset_otp
                    and len(new_pass) >= 6
                ):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (
                            hash_password(new_pass),
                            st.session_state.reset_user,
                        ),
                    )
                    conn.commit()
                    conn.close()

                    st.success(
                        "Password successfully updated! Please switch to Login tab."
                    )
                    st.session_state.reset_otp = None
                    st.session_state.reset_user = None
                else:
                    st.error("Invalid OTP or Password must be 6+ characters.")

else:
    st.sidebar.title(f"👤 {st.session_state.full_name}")
    st.sidebar.caption(f"Role: **{st.session_state.role}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.role == "ADMIN":
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "🎥 Live Stream",
                "🖼️ Image Scanner",
                "📋 Wanted Registry",
                "📊 Audit Logs",
                "👥 User Management",
            ]
        )
    else:
        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "🎥 Live Stream",
                "🖼️ Image Scanner",
                "📋 Wanted Registry",
                "📊 Audit Logs",
            ]
        )

    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📹 Checkpost Live Feed")
            run_cam = st.checkbox("Turn On ANPR Camera Feed")
            FRAME_WINDOW = st.image([])
            if run_cam:
                cap = cv2.VideoCapture(0)
                while run_cam:
                    ret, frame = cap.read()
                    if not ret:
                        st.error("Camera feed offline.")
                        break
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    FRAME_WINDOW.image(frame_rgb)
                cap.release()

        with col2:
            st.subheader("🚨 Security Alerts")
            st.info("System Ready. Monitoring active feed...")

    with tab2:
        st.subheader("🔍 Scan Vehicle Image")
        uploaded_file = st.file_uploader(
            "Upload Image", type=["jpg", "jpeg", "png"]
        )
        if uploaded_file:
            file_bytes = np.asarray(
                bytearray(uploaded_file.read()), dtype=np.uint8
            )
            image = cv2.imdecode(file_bytes, 1)

            c1, c2 = st.columns(2)
            with c1:
                st.image(
                    image, channels="BGR", caption="Uploaded Vehicle Image"
                )
            with c2:
                with st.spinner("Processing OCR & Database Check..."):
                    results = reader.readtext(image)
                    if results:
                        detected_text = " ".join([res[1] for res in results])
                        st.success(
                            f"**Detected Plate Number:** `{detected_text}`"
                        )

                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM stolen_vehicles WHERE plate_number = ?",
                            (detected_text.strip(),),
                        )
                        record = cursor.fetchone()
                        conn.close()

                        if record:
                            st.error(
                                "🚨 ALERT: STOLEN / WANTED VEHICLE DETECTED!"
                            )
                            st.write(f"**Model:** {record[2]}")
                            st.write(f"**Color:** {record[3]}")
                            st.write(f"**Engine No:** {record[4]}")
                            st.write(f"**Chassis No:** {record[5]}")
                            st.write(f"**Owner:** {record[6]}")
                            st.write(f"**FIR Reference:** {record[7]}")
                        else:
                            st.info("✅ Vehicle status clean.")
                    else:
                        st.warning("No license plate detected.")

    with tab3:
        st.subheader("📝 Register Wanted Vehicle")
        with st.form("add_veh"):
            p_num = st.text_input("Plate Number (e.g., LEA-1234)").upper()
            v_mod = st.text_input("Vehicle Make & Model")
            v_col = st.text_input("Vehicle Color")
            eng_num = st.text_input("Engine Number")
            chas_num = st.text_input("Chassis Number")
            owner = st.text_input("Owner Name")
            fir = st.text_input("FIR Number")
            sub = st.form_submit_button("Add to Registry")

            if sub:
                if p_num and fir:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO stolen_vehicles 
                            (plate_number, vehicle_model, vehicle_color, engine_number, chassis_number, owner_name, fir_number)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                p_num.strip(),
                                v_mod.strip(),
                                v_col.strip(),
                                eng_num.strip(),
                                chas_num.strip(),
                                owner.strip(),
                                fir.strip(),
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            f"Vehicle `{p_num}` registered successfully!"
                        )
                    except sqlite3.IntegrityError:
                        st.error("Plate number already exists.")
                else:
                    st.error("Plate Number & FIR Number are mandatory.")

        st.markdown("---")
        st.subheader("📑 Blacklisted Vehicles Database")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

    with tab4:
        st.subheader("📊 Audit Reports & Export")
        conn = get_db_connection()
        df_logs = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
        conn.close()
        csv = df_logs.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Full Registry (CSV)",
            csv,
            "AutoPlate_Report.csv",
            "text/csv",
        )

    if st.session_state.role == "ADMIN":
        with tab5:
            st.subheader("👥 Register New Staff / Duty Officer")
            with st.form("add_user_form"):
                f_name = st.text_input("Full Name")
                b_num = st.text_input("Belt / ID Number")
                u_email = st.text_input("Official Email (Gmail)")
                u_name = st.text_input("Username")
                u_pass = st.text_input("Initial Password", type="password")
                u_role = st.selectbox("Role", ["STAFF", "ADMIN"])
                u_sub = st.form_submit_button("Create User Account")

                if u_sub:
                    if u_name and u_pass and u_email:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT INTO users (full_name, belt_number, email, username, password, role)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    f_name.strip(),
                                    b_num.strip(),
                                    u_email.strip(),
                                    u_name.strip(),
                                    hash_password(u_pass),
                                    u_role,
                                ),
                            )
                            conn.commit()
                            conn.close()
                            st.success(
                                f"Account for `{u_name}` created as {u_role}!"
                            )
                        except sqlite3.IntegrityError:
                            st.error("Username or Email already exists.")
                    else:
                        st.error("All fields are required.")

            st.markdown("---")
            st.subheader("📋 Registered System Users")
            conn = get_db_connection()
            df_users = pd.read_sql_query(
                "SELECT id, full_name, belt_number, email, username, role FROM users",
                conn,
            )
            conn.close()
            st.dataframe(df_users, use_container_width=True)
            
