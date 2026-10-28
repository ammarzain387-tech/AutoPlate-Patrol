import cv2
import easyocr
import re

# Initialize EasyOCR Engine for License Plate Recognition
print("⏳ Initializing EasyOCR Engine...")
reader = easyocr.Reader(['en'], gpu=False)
print("✅ EasyOCR Engine Loaded Successfully!")

def clean_plate_text(text):
    """Converts OCR text to uppercase and keeps alphanumeric characters only."""
    return re.sub(r'[^A-Z0-9]', '', text.upper())

# Open Webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Error: Could not open camera.")
    exit()

print("🚀 AutoPlate Patrol Active!")
print("Press 'S' on keyboard to scan plate | Press 'Q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # On-screen instructions
    cv2.putText(
        frame,
        "Press 'S' to Scan Plate | 'Q' to Quit",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.imshow("AutoPlate Patrol - Islamabad Police ANPR", frame)

    key = cv2.waitKey(1) & 0xFF

    # Press 's' to capture and process plate
    if key == ord('s'):
        print("\n📸 Scanning current frame for license plate...")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        results = reader.readtext(gray)

        if not results:
            print("⚠️ No readable text found in frame.")
        else:
            print("--- SCANNED RESULTS ---")
            for (bbox, text, prob) in results:
                if prob > 0.3:  # Filter low confidence OCR reads
                    cleaned = clean_plate_text(text)
                    if len(cleaned) >= 3:
                        print(f"🚘 Detected Plate: {cleaned} (Confidence: {prob*100:.1f}%)")

                        # Draw bounding box
                        (top_left, top_right, bottom_right, bottom_left) = bbox
                        top_left = (int(top_left[0]), int(top_left[1]))
                        bottom_right = (int(bottom_right[0]), int(bottom_right[1]))

                        cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
                        cv2.putText(
                            frame,
                            f"PLATE: {cleaned}",
                            (top_left[0], top_left[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2
                        )

            cv2.imshow("Scanned Result", frame)

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("👋 AutoPlate Patrol Stopped.")