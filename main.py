import cv2
import easyocr
import re
import time
from database import init_db, check_stolen_status, log_detection

# Initialize SQLite Database
init_db()

# Initialize EasyOCR Reader Engine
print("⏳ Initializing Islamabad Police Checkpost ANPR System...")
reader = easyocr.Reader(['en'], gpu=False)
print("✅ ANPR System Active and Ready!")

def clean_plate_text(text):
    """Clean OCR output to match uppercase alphanumeric plate format."""
    return re.sub(r'[^A-Z0-9]', '', text.upper())

# Connect to Checkpost Camera Feed
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Error: Could not connect to Checkpost Camera.")
    exit()

# System variables
last_scan_time = 0
SCAN_INTERVAL = 1.5  # Scan interval in seconds
alert_display_timer = 0
alert_info = None

print("🚀 Islamabad Police ANPR Checkpost Feed Running...")
print("Press 'q' to stop system.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Camera feed disconnected.")
        break

    current_time = time.time()

    # Automatic periodic scanning for incoming vehicles
    if current_time - last_scan_time > SCAN_INTERVAL:
        last_scan_time = current_time
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        results = reader.readtext(gray)

        for (bbox, text, prob) in results:
            if prob > 0.35:
                cleaned_plate = clean_plate_text(text)
                
                if len(cleaned_plate) >= 3:
                    # Query Database for Stolen Status
                    record = check_stolen_status(cleaned_plate)
                    
                    if record:
                        owner, model, status = record
                        alert_info = {
                            'plate': cleaned_plate,
                            'owner': owner,
                            'model': model,
                            'status': status
                        }
                        alert_display_timer = time.time()
                        
                        # Log Stolen Detection to Database
                        log_detection(cleaned_plate, "STOLEN_DETECTED", float(prob))
                        print(f"\n🚨 ALERT! STOLEN VEHICLE DETECTED & LOGGED: {cleaned_plate} | Owner: {owner}")
                    else:
                        # Log Normal Pass to Database
                        log_detection(cleaned_plate, "CLEAR", float(prob))
                        print(f"✅ Vehicle Passed & Logged: {cleaned_plate} (CLEAR)")

    # -----------------------------------------------------------------
    # ON-SCREEN GUI DISPLAY OVERLAY
    # -----------------------------------------------------------------
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (30, 30, 30), -1)
    cv2.putText(
        frame,
        "ISLAMABAD POLICE - ANPR CHECKPOST MONITOR",
        (15, 33),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    if alert_info and (time.time() - alert_display_timer < 4.0):
        cv2.rectangle(frame, (10, 60), (frame.shape[1] - 10, 160), (0, 0, 255), -1)
        cv2.putText(
            frame,
            f"🚨 WANTED VEHICLE DETECTED: {alert_info['plate']}",
            (20, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )
        cv2.putText(
            frame,
            f"Owner: {alert_info['owner']} | Model: {alert_info['model']} | Status: {alert_info['status']}",
            (20, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

    cv2.imshow("Islamabad Police Checkpost Live ANPR Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("👋 ANPR Checkpost System Shutdown.")