import json
import os
import uuid
import io
import qrcode
from datetime import datetime
from typing import Dict, Any, List, Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "db.json")

DEFAULT_DOCTORS = [
    {
        "id": "doc_1",
        "name": "Dr. Sarah Jenkins",
        "specialty": "Cardiology",
        "qualification": "MD, FACC",
        "hospital": "MediSync Heart Center",
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "available_time": "09:00 AM - 04:00 PM",
        "avatar": "👩‍⚕️"
    },
    {
        "id": "doc_2",
        "name": "Dr. Rajiv Mehta",
        "specialty": "Endocrinology & Diabetology",
        "qualification": "MD, DM (Endo)",
        "hospital": "MediSync Metabolic Clinic",
        "available_days": ["Mon", "Wed", "Fri", "Sat"],
        "available_time": "10:00 AM - 05:00 PM",
        "avatar": "👨‍⚕️"
    },
    {
        "id": "doc_3",
        "name": "Dr. Elena Rostova",
        "specialty": "General Internal Medicine",
        "qualification": "MBBS, MD",
        "hospital": "MediSync Primary Care",
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "available_time": "08:30 AM - 03:30 PM",
        "avatar": "👩‍⚕️"
    },
    {
        "id": "doc_4",
        "name": "Dr. Marcus Chen",
        "specialty": "Pulmonology & Respiratory Care",
        "qualification": "MD, FCCP",
        "hospital": "MediSync Pulmonary Care",
        "available_days": ["Tue", "Thu", "Sat"],
        "available_time": "11:00 AM - 06:00 PM",
        "avatar": "👨‍⚕️"
    }
]

class RecordsStore:
    def __init__(self):
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        if not os.path.exists(DATA_FILE):
            initial_data = {
                "doctors": DEFAULT_DOCTORS,
                "reports": {},
                "appointments": []
            }
            self._save(initial_data)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"doctors": DEFAULT_DOCTORS, "reports": {}, "appointments": []}

    def _save(self, data: Dict[str, Any]):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_doctors(self) -> List[Dict[str, Any]]:
        data = self._load()
        return data.get("doctors", DEFAULT_DOCTORS)

    def get_doctor_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for d in self.get_doctors():
            if d["id"] == doc_id:
                return d
        return None

    def save_report(self, report_data: Dict[str, Any]) -> str:
        data = self._load()
        report_id = report_data.get("id") or f"rep_{uuid.uuid4().hex[:8]}"
        report_data["id"] = report_id
        report_data["token"] = report_data.get("token") or f"TK-{uuid.uuid4().hex[:6].upper()}"
        report_data["created_at"] = report_data.get("created_at") or datetime.now().isoformat()
        
        data["reports"][report_id] = report_data
        self._save(data)
        return report_id

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data.get("reports", {}).get(report_id)

    def get_report_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        token_upper = token.strip().upper()
        for r_id, r in data.get("reports", {}).items():
            if r.get("token", "").upper() == token_upper or r_id == token:
                return r
        return None

    def list_reports(self, patient_name: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._load()
        reports = list(data.get("reports", {}).values())
        if patient_name:
            reports = [r for r in reports if patient_name.lower() in r.get("patient_name", "").lower()]
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return reports

    def add_doctor_notes(self, report_id: str, doctor_name: str, notes: str) -> bool:
        data = self._load()
        if report_id in data.get("reports", {}):
            report = data["reports"][report_id]
            doctor_entries = report.get("doctor_notes", [])
            doctor_entries.append({
                "id": str(uuid.uuid4()),
                "doctor_name": doctor_name,
                "notes": notes,
                "created_at": datetime.now().isoformat()
            })
            report["doctor_notes"] = doctor_entries
            self._save(data)
            return True
        return False

    def book_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        appt_id = f"apt_{uuid.uuid4().hex[:8]}"
        appointment_data["id"] = appt_id
        appointment_data["created_at"] = datetime.now().isoformat()
        appointment_data["status"] = appointment_data.get("status", "Confirmed")
        
        data["appointments"].append(appointment_data)
        self._save(data)
        return appointment_data

    def list_appointments(self, doctor_id: Optional[str] = None, patient_name: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._load()
        appts = data.get("appointments", [])
        if doctor_id:
            appts = [a for a in appts if a.get("doctor_id") == doctor_id]
        if patient_name:
            appts = [a for a in appts if patient_name.lower() in a.get("patient_name", "").lower()]
        appts.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
        return appts

    def update_appointment_status(self, appt_id: str, new_status: str) -> bool:
        data = self._load()
        for a in data.get("appointments", []):
            if a.get("id") == appt_id:
                a["status"] = new_status
                self._save(data)
                return True
        return False

    def generate_qr_code(self, token: str, base_url: str = "http://127.0.0.1:8000") -> bytes:
        qr_url = f"{base_url}/?portal=doctor&token={token}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0F766E", back_color="#FFFFFF")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

records_store = RecordsStore()

