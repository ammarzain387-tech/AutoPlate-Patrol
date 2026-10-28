import streamlit as st
import cv2
import numpy as np
import easyocr
import sqlite3
import pandas as pd
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Automated Stolen & Wanted Vehicle Recognition System",
    page_icon="🚔",
    layout="wide",
)

# Custom CSS for Professional Police Dashboard Styling
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
        font-size: 16px;
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
    unsafe_allow_javascript=True,
)

# Render Header Banner
st.markdown(
    """
    <div class="main-header">
        <h1>AUTOMATED STOLEN & WANTED VEHICLE RECOGNITION SYSTEM</h1>
        <h3>ISLAMABAD POLICE — COMMAND & CONTROL DASHBOARD</h3>
    </div>
""",
    unsafe_allow_javascript=True,
)


# Initialize Database Connection
def get_db_connection():
    conn = sqlite3.connect("stolen_vehicles.db", check_same_thread=False)
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stolen_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            vehicle_model TEXT,
            owner_name TEXT,
            fir_number TEXT,
            status TEXT DEFAULT 'WANTED'
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


# Initialize EasyOCR Reader
@st.cache_resource
def load_ocr():
    return easyocr.Reader(["en"])


reader = load_ocr()

# Top Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🎥 Live Camera Stream",
        "🖼️ Image File Scanner",
        "📋 Wanted Vehicles Registry",
        "📊 Audit Logs & Alert Center",
    ]
)

# Tab 1: Live Camera Stream
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📹 Checkpost Live Feed")
        run_camera = st.checkbox("Turn On ANPR Camera Feed")
        FRAME_WINDOW = st.image([])

        if run_camera:
            cap = cv2.VideoCapture(0)
            while run_camera:
                ret, frame = cap.read()
                if not ret:
                    st.error("Failed to access camera stream.")
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                FRAME_WINDOW.image(frame_rgb)
            cap.release()

    with col2:
        st.subheader("🚨 Real-Time Security Alerts")
        st.info("System Ready. Monitoring active checkpost feed...")

# Tab 2: Image File Scanner
with tab2:
    st.subheader("🔍 Upload Vehicle Image for Recognition")
    uploaded_file = st.file_uploader(
        "Choose an image file...", type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        file_bytes = np.asarray(
            bytearray(uploaded_file.read()), dtype=np.uint8
        )
        image = cv2.imdecode(file_bytes, 1)

        col_img, col_res = st.columns(2)
        with col_img:
            st.image(image, channels="BGR", caption="Uploaded Vehicle Image")

        with col_res:
            st.subheader("ANPR Scanning Results")
            with st.spinner("Processing OCR & Database Check..."):
                results = reader.readtext(image)

                if results:
                    detected_text = " ".join([res[1] for res in results])
                    st.success(f"**Detected Plate Number:** `{detected_text}`")

                    # Check in Database
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM stolen_vehicles WHERE plate_number = ?",
                        (detected_text.strip(),),
                    )
                    record = cursor.fetchone()
                    conn.close()

                    if record:
                        st.error("🚨 ALERT: STOLEN / WANTED VEHICLE DETECTED!")
                        st.write(f"**Vehicle Model:** {record[2]}")
                        st.write(f"**Registered Owner:** {record[3]}")
                        st.write(f"**FIR Number:** {record[4]}")
                    else:
                        st.info(
                            "✅ Vehicle status clean. No match found in wanted database."
                        )
                else:
                    st.warning("No clear license plate text detected.")

# Tab 3: Wanted Vehicles Registry
with tab3:
    st.subheader("📝 Register New Stolen / Wanted Vehicle")

    with st.form("add_vehicle_form"):
        plate_num = st.text_input("Plate Number (e.g., LEA-1234)").upper()
        veh_model = st.text_input("Vehicle Make & Model (e.g., Toyota Corolla)")
        owner_name = st.text_input("Registered Owner Name")
        fir_num = st.text_input("FIR / Case Reference Number")
        submitted = st.form_submit_button("Add to Blacklist Registry")

        if submitted:
            if plate_num and fir_num:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO stolen_vehicles (plate_number, vehicle_model, owner_name, fir_number) VALUES (?, ?, ?, ?)",
                        (
                            plate_num.strip(),
                            veh_model.strip(),
                            owner_name.strip(),
                            fir_num.strip(),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(
                        f"Vehicle `{plate_num}` successfully added to Wanted Database!"
                    )
                except sqlite3.IntegrityError:
                    st.error("Plate number already exists in registry.")
            else:
                st.error(
                    "Please fill in all mandatory fields (Plate Number & FIR Number)."
                )

    st.markdown("---")
    st.subheader("📑 Current Wanted Vehicles List")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

# Tab 4: Audit Logs & Export
with tab4:
    st.subheader("📊 System Logs & Reports Export")
    st.write(
        "Generate & download official security audit reports for departmental review."
    )

    conn = get_db_connection()
    df_logs = pd.read_sql_query("SELECT * FROM stolen_vehicles", conn)
    conn.close()

    csv = df_logs.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Full Registry Report (CSV)",
        data=csv,
        file_name="Stolen_Vehicles_Report.csv",
        mime="text/csv",
    )
