import streamlit as st
import cv2
import easyocr
import re
import time
import pandas as pd
import sqlite3
from PIL import Image
import numpy as np
from database import (
    init_db, 
    check_stolen_status, 
    log_detection, 
    add_stolen_vehicle, 
    remove_stolen_vehicle
)

# Page Setup
st.set_page_config(
    page_title="Islamabad Police ANPR Portal",
    layout="wide",
    page_icon="🚔",
    initial_sidebar_state="expanded"
)

init_db()

# Custom CSS Banner (Fixed Typo Here)
st.markdown("""
    <style>
    .main-header {
        font-size: 28px;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        padding: 10px;
        background-color: #E0F2FE;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    <div class="main-header">🚔 ISLAMABAD POLICE — AUTOPLATE PATROL ANPR SYSTEM</div>
""", unsafe_allow_html=True)

# Load EasyOCR Engine
@st.cache_resource
def load_ocr():
    with st.spinner("⏳ Loading ANPR Recognition Engine..."):
        return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

def clean_plate_text(text):
    return re.sub(r'[^A-Z0-9]', '', text.upper())

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📹 Live Camera Stream", 
    "🖼️ Image File Scanner", 
    "📋 Wanted Vehicles Registry", 
    "📊 Audit Logs & Export"
])

# =====================================================================
# TAB 1: LIVE CAMERA STREAM
# =====================================================================
with tab1:
    col_cam, col_alert = st.columns([2, 1])

    with col_cam:
        st.subheader("📹 Checkpost Live Feed")
        run_cam = st.checkbox("Turn On ANPR Camera Feed", value=False)
        FRAME_WINDOW = st.image([])

    with col_alert:
        st.subheader("🚨 Real-Time Security Alerts")
        alert_box = st.empty()

    if run_cam:
        cap = cv2.VideoCapture(0)
        last_scan_time = 0

        while run_cam:
            ret, frame = cap.read()
            if not ret:
                st.error("❌ Camera Connection Failed.")
                break

            current_time = time.time()

            # Automatic Scanning Interval (1.5 sec)
            if current_time - last_scan_time > 1.5:
                last_scan_time = current_time
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                results = reader.readtext(gray)

                for (bbox, text, prob) in results:
                    if prob > 0.35:
                        cleaned_plate = clean_plate_text(text)
                        if len(cleaned_plate) >= 3:
                            record = check_stolen_status(cleaned_plate)
                            if record:
                                owner, model, status = record
                                log_detection(cleaned_plate, "STOLEN_DETECTED", float(prob))
                                alert_box.error(
                                    f"🚨 **WANTED VEHICLE DETECTED!**\n\n"
                                    f"**Plate:** `{cleaned_plate}`\n\n"
                                    f"**Owner:** {owner}\n\n"
                                    f"**Vehicle:** {model}\n\n"
                                    f"**Status:** {status}"
                                )
                            else:
                                log_detection(cleaned_plate, "CLEAR", float(prob))
                                alert_box.success(f"✅ **Vehicle Cleared:** `{cleaned_plate}`")

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            FRAME_WINDOW.image(frame_rgb)

        cap.release()

# =====================================================================
# TAB 2: IMAGE FILE SCANNER
# =====================================================================
with tab2:
    st.subheader("📸 Scan Vehicle Photo On-Demand")
    uploaded_file = st.file_uploader("Upload Vehicle Image (JPG/PNG)", type=['jpg', 'jpeg', 'png'])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        img_np = np.array(image)

        col_img, col_res = st.columns(2)
        with col_img:
            st.image(image, caption="Uploaded Image", use_column_width=True)

        with col_res:
            st.write("🔍 **Scanning Image for License Plates...**")
            results = reader.readtext(img_np)

            if not results:
                st.warning("⚠️ No clear license plate detected in image.")
            else:
                for (bbox, text, prob) in results:
                    if prob > 0.3:
                        cleaned = clean_plate_text(text)
                        if len(cleaned) >= 3:
                            st.info(f"🚘 **Detected Plate:** `{cleaned}` (Confidence: {prob*100:.1f}%)")
                            record = check_stolen_status(cleaned)
                            if record:
                                owner, model, status = record
                                log_detection(cleaned, "STOLEN_DETECTED", float(prob))
                                st.error(
                                    f"🚨 **MATCH FOUND IN POLICE DATABASE!**\n\n"
                                    f"**Owner Name:** {owner}\n\n"
                                    f"**Vehicle Model:** {model}\n\n"
                                    f"**Status:** {status}"
                                )
                            else:
                                log_detection(cleaned, "CLEAR", float(prob))
                                st.success("✅ **Vehicle Status:** CLEAR (Not in Wanted Registry)")

# =====================================================================
# TAB 3: STOLEN VEHICLES REGISTRY MANAGEMENT
# =====================================================================
with tab3:
    col_add, col_list = st.columns([1, 2])

    with col_add:
        st.subheader("➕ Register Stolen Vehicle FIR")
        with st.form("add_vehicle_form"):
            new_plate = st.text_input("License Plate Number (e.g. ICT789)")
            new_owner = st.text_input("Owner Name")
            new_model = st.text_input("Vehicle Model (e.g. Honda Civic)")
            submit_btn = st.form_submit_button("Add to Police Database")

            if submit_btn:
                if new_plate and new_owner and new_model:
                    success, msg = add_stolen_vehicle(new_plate, new_owner, new_model)
                    if success:
                        st.success(msg)
                    else:
                        st.warning(msg)
                else:
                    st.error("Please fill all fields.")

    with col_list:
        st.subheader("📋 Registered Wanted Vehicles List")
        conn = sqlite3.connect("stolen_vehicles.db")
        df_stolen = pd.read_sql_query("SELECT id, plate_number, owner_name, vehicle_model, status FROM stolen_vehicles", conn)
        conn.close()
        st.dataframe(df_stolen, use_container_width=True)

        # Delete Option
        remove_plate = st.text_input("Enter Plate Number to Remove FIR Record:")
        if st.button("Remove Vehicle Record"):
            if remove_plate:
                res_msg = remove_stolen_vehicle(remove_plate)
                st.success(res_msg)
                st.rerun()

# =====================================================================
# TAB 4: AUDIT LOGS & EXPORT REPORT
# =====================================================================
with tab4:
    st.subheader("📊 Checkpost Detection History Logs")
    conn = sqlite3.connect("stolen_vehicles.db")
    df_logs = pd.read_sql_query("SELECT * FROM detection_logs ORDER BY id DESC", conn)
    conn.close()

    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)

        # Export CSV Button
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Detection Logs (CSV Report)",
            data=csv,
            file_name="Islamabad_Police_ANPR_Logs.csv",
            mime="text/csv"
        )
    else:
        st.info("No detection logs available yet.")