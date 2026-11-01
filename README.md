# 🚔 AutoPlate Patrol — ANPR Command Center

**AutoPlate Patrol** is an Automatic Number Plate Recognition (ANPR) system built with Streamlit, OpenCV, EasyOCR, and SQLite. It provides automated detection of vehicle license plates, real-time alerts against blacklisted/stolen vehicle registries, and secure staff management.

---

## 🚀 Key Features

- **Automated License Plate Recognition (ANPR)**: Optical Character Recognition (OCR) to read vehicle plates from uploaded images.
- **Stolen & Wanted Vehicle Alerts**: Instant cross-referencing with local databases for FIR and owner details.
- **Role-Based Access Control**: Separate privileges for System Administrators and Duty Officers.
- **Duty Officer Recovery**: Secure verification workflow for officer account recovery.
- **Audit Reports**: Real-time registry tracking with CSV report exports.
- **Staff Management**: Admin dashboard to onboard new field officers.

---

## 🛠️ Tech Stack

- **Frontend & Web Framework**: Streamlit
- **Computer Vision & OCR**: OpenCV, EasyOCR, NumPy
- **Database**: SQLite3
- **Data Handling**: Pandas
- **Language**: Python 3.x

---

## 📂 Repository Structure

```text
.
├── app.py                # Core application entry point
├── requirements.txt      # Dependencies
├── stolen_vehicles.db    # SQLite database (Auto-initialized)
└── README.md             # Project documentation

⚙️ Installation & Usage

1.   Clone Repository:
git clone [https://github.com/your-ammarzain387-tech/AutoPlate-Patrol.git](https://github.com/ammarzain387-tech/AutoPlate-Patrol.git)
cd AutoPlate-Patrol

2.   Istall Dependencies:
pip install -r requirements.txt

3.   Run Application:
streamlit run app.py

🔐 Default Access Credentials
Admin Username: admin

Admin Password: Admin@123

Default Belt ID: ADMIN-01

📜 License
Developed for law enforcement, field security monitoring, and automated vehicle surveillance.
