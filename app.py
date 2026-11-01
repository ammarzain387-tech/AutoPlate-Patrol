 import sqlite3
import hashlib
import cv2
import numpy as np
import pandas as pd
import streamlit as st
import easyocr

# Page Configuration
st.set_page_config(
    page_title="AutoPlate Patrol — ANPR System",
    page_icon="🚔",
    layout="wide"
)

# Initialize EasyOCR Reader (Cached for optimal performance)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'])

reader = load_ocr_reader()

# Database Setup
DB_NAME = "stolen_vehicles.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            belt_number TEXT,
            email TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    
    # Create stolen_vehicles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stolen_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE,
            vehicle_model TEXT,
            vehicle_color TEXT,
            engine_number TEXT,
            chassis_number TEXT,
            owner_name TEXT,
            fir_number TEXT
        )
    ''')
    
    # Insert Default Admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (full_name, belt_number, email, username, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("System Administrator", "ADMIN-01", "admin@autoplate.org", "admin", hash_password("Admin@123"), "ADMIN"))
    
    conn.commit()
    conn.close()

init_db()

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# Application Header
st.title("🚔 AUTOPLATE PATROL — ANPR COMMAND CENTER")
st.caption("AUTOMATED STOLEN & WANTED VEHICLE RECOGNITION SYSTEM")
st.markdown("---")

# Sidebar Status
with st.sidebar:
    st.header("🔐 Access Control")
    if st.session_state.logged_in:
        st.success(f"Logged in as: **{st.session_state.username}** ({st.session_state.role})")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()
    else:
        st.info("Please login from the main portal.")

# Main Portal Layout
if not st.session_state.logged_in:
    tab_login, tab_reset = st.tabs(["👮 Duty Officer Login", "🔑 Forgot / Reset Password"])
    
    # LOGIN TAB
    with tab_login:
        st.subheader("System Access Portal")
        with st.form("login_form"):
            u_input = st.text_input("Username")
            p_input = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn:
                if u_input and p_input:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT username, role, password FROM users WHERE username = ?",
                        (u_input.strip(),)
                    )
                    user = cursor.fetchone()
                    conn.close()
                    
                    if user and user[2] == hash_password(p_input):
                        st.session_state.logged_in = True
                        st.session_state.username = user[0]
                        st.session_state.role = user[1]
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                else:
                    st.error("Please enter both Username and Password.")
                    
    # PASSWORD RESET TAB (BELT NUMBER VERIFICATION)
    with tab_reset:
        st.subheader("🔑 Duty Officer Password Recovery")
        st.caption("Verify your identity using your Official Belt / ID Number.")
        
        with st.form("reset_password_form"):
            r_username = st.text_input("Registered Username")
            r_belt = st.text_input("Official Belt / ID Number")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            reset_btn = st.form_submit_button("Reset & Update Password")
            
            if reset_btn:
                if r_username and r_belt and new_pass and confirm_pass:
                    if new_pass != confirm_pass:
                        st.error("❌ Passwords do not match!")
                    else:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM users WHERE username = ? AND belt_number = ?",
                            (r_username.strip(), r_belt.strip())
                        )
                        user = cursor.fetchone()
                        
                        if user:
                            hashed_p = hash_password(new_pass)
                            cursor.execute(
                                "UPDATE users SET password = ? WHERE id = ?",
                                (hashed_p, user[0])
                            )
                            conn.commit()
                            conn.close()
                            st.success("✅ Password updated successfully! You can now login with your new password.")
                        else:
                            conn.close()
                            st.error("❌ Invalid Username or Belt / ID Number combination.")
                else:
                    st.error("⚠️ All fields are mandatory.")

else:
    # LOGGED IN DASHBOARD
    tabs_list = ["🔍 Scan Vehicle Image", "📝 Register Wanted Vehicle", "📊 Audit Reports"]
    if st.session_state.role == "ADMIN":
        tabs_list.append("👥 Staff Management")
        
    tabs = st.tabs(tabs_list)
    
    # TAB 1: SCAN VEHICLE (ANPR)
    with tabs[0]:
        st.subheader("🔍 Scan Vehicle Image (ANPR)")
        uploaded_file = st.file_uploader("Upload Vehicle Image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, 1)
            
            c1, c2 = st.columns(2)
            with c1:
                st.image(image, channels="BGR", caption="Uploaded Vehicle Image", use_container_width=True)
            
            with c2:
                with st.spinner("Processing OCR & Database Check..."):
                    results = reader.readtext(image)
                    if results:
                        detected_text = "".join([res[1] for res in results]).replace(" ", "").upper()
                        st.success(f"**Detected Plate Number:** `{detected_text}`")
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM stolen_vehicles WHERE REPLACE(plate_number, ' ', '') = ?",
                            (detected_text,)
                        )
                        record = cursor.fetchone()
                        conn.close()
                        
                        if record:
                            st.error("🚨 ALERT: STOLEN / WANTED VEHICLE DETECTED!")
                            st.write(f"**Plate:** {record[1]}")
                            st.write(f"**Model:** {record[2]}")
                            st.write(f"**Color:** {record[3]}")
                            st.write(f"**Engine No:** {record[4]}")
                            st.write(f"**Chassis No:** {record[5]}")
                            st.write(f"**Owner:** {record[6]}")
                            st.write(f"**FIR Reference:** {record[7]}")
                        else:
                            st.info("✅ Vehicle status clean.")
                    else:
                        st.warning("No license plate detected in the uploaded image.")

    # TAB 2: REGISTER WANTED VEHICLE
    with tabs[1]:
        st.subheader("📝 Register Wanted Vehicle")
        with st.form("add_veh_form"):
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
                        cursor.execute('''
                            INSERT INTO stolen_vehicles 
                            (plate_number, vehicle_model, vehicle_color, engine_number, chassis_number, owner_name, fir_number)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (p_num.strip(), v_mod.strip(), v_col.strip(), eng_num.strip(), chas_num.strip(), owner.strip(), fir.strip()))
                        conn.commit()
                        conn.close()
                        st.success(f"Vehicle `{p_num}` registered successfully!")
                    except sqlite3.IntegrityError:
                        st.error("Plate number already exists in the registry.")
                else:
                    st.error("Plate Number and FIR Number are mandatory.")
                    
        st.markdown("---")
        st.subheader("📑 Blacklisted Vehicles Registry")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)

    # TAB 3: AUDIT REPORTS
    with tabs[2]:
        st.subheader("📊 Audit Reports & Data Export")
        conn = get_db_connection()
        df_logs = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
        conn.close()
        
        st.dataframe(df_logs, use_container_width=True)
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Export Full Registry (CSV)",
            csv,
            "AutoPlate_Report.csv",
            "text/csv"
        )

    # TAB 4: STAFF MANAGEMENT (ADMIN ONLY)
    if st.session_state.role == "ADMIN":
        with tabs[3]:
            st.subheader("👥 Register New Staff / Duty Officer")
            with st.form("add_user_form"):
                f_name = st.text_input("Full Name")
                b_num = st.text_input("Belt / ID Number")
                u_email = st.text_input("Official Email")
                u_name = st.text_input("Username")
                u_pass = st.text_input("Initial Password", type="password")
                u_role = st.selectbox("Role", ["STAFF", "ADMIN"])
                u_sub = st.form_submit_button("Create User Account")
                
                if u_sub:
                    if u_name and u_pass and b_num:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO users (full_name, belt_number, email, username, password, role)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (f_name.strip(), b_num.strip(), u_email.strip(), u_name.strip(), hash_password(u_pass), u_role))
                            conn.commit()
                            conn.close()
                            st.success(f"Account for `{u_name}` created successfully as {u_role}!")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists.")
                    else:
                        st.error("Username, Belt Number, and Password are required.")
                        
            st.markdown("---")
            st.subheader("📋 Registered System Users")
            conn = get_db_connection()
            df_users = pd.read_sql_query("SELECT id, full_name, belt_number, email, username, role FROM users", conn)
            conn.close()
            st.dataframe(df_users, use_container_width=True)         
