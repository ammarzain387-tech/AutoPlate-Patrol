import hashlib
import random
import sqlite3
import cv2
import easyocr
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

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


# Helper: Password Hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Database Connection & Initialization
def get_db_connection():
    return sqlite3.connect("stolen_vehicles.db", check_same_thread=False)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vehicles Table (Upgraded)
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

    # Users Table (RBAC)
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

    # Default Admin Creation
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


# OCR Loader
@st.cache_resource
def load_ocr():
    return easyocr.Reader(["en"])


reader = load_ocr()

# Session State for Authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.full_name = ""

# Universal Header Banner
st.markdown(
    """
    <div class="main-header">
        <h1>AUTOPLATE PATROL — ANPR COMMAND CENTER</h1>
        <h3>AUTOMATED STOLEN & WANTED VEHICLE RECOGNITION SYSTEM</h3>
    </div>
""",
    unsafe_allow_html=True,
)

# Authentication Routing
if not st.session_state.logged_in:
    st.subheader("🔐 Duty Officer & Admin Login Portal")
    col_login, col_info = st.columns([1, 1])

    with col_login:
        login_user = st.text_input("Username")
        login_pass = st.text_input("Password", type="password")
        if st.button("Login to Portal"):
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
                    st.success(f"Welcome, {user[0]} ({user[1]})!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")
            else:
                st.warning("Please enter both username and password.")

    with col_info:
        st.info(
            """
            **Default Admin Credentials (For First Login):**
            - **Username:** `admin`
            - **Password:** `Admin@123`
            
            *Admin users can create staff accounts and manage registries.*
        """
        )

else:
    # Sidebar Profile & Logout
    st.sidebar.title(f"👤 {st.session_state.full_name}")
    st.sidebar.caption(f"Role: **{st.session_state.role}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # Navigation Tabs based on Role
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

    # Tab 1: Live Stream
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

    # Tab 2: Image Scanner
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

    # Tab 3: Wanted Registry
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

    # Tab 4: Audit Logs
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

    # Tab 5: User Management (Admin Only)
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
