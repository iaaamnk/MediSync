import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from backend.records_store import records_store
from backend.gemini_analyzer import gemini_analyzer
from backend.voice_pipeline import voice_pipeline
from backend.security import inspect_request_for_bots, verify_honeypot

app = FastAPI(
    title="MediSync Hospital Dashboard API",
    description="Hospital Dashboard System with Patient Portal, Doctor Portal, Gemini Medical Report Analyzer, QR Code Access, Voice Pipeline, and Appointment Booking.",
    version="1.0.0"
)

# Bot Protection & Security Headers Middleware
@app.middleware("http")
async def bot_and_security_middleware(request: Request, call_next):
    # 1. Anti-Bot and Scraper Inspection
    bot_block_response = inspect_request_for_bots(request)
    if bot_block_response:
        return bot_block_response

    # 2. Process Request
    response = await call_next(request)

    # 3. Add Defensive Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=*, camera=*"
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Robots.txt to instruct compliant crawlers to avoid sensitive records
@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots_txt():
    return """User-agent: *
Disallow: /api/
Disallow: /uploads/
Disallow: /*?token=*
"""

# Pydantic Schemas
class DoctorNotesRequest(BaseModel):
    doctor_name: str
    notes: str

class AppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_id: str
    date: str
    time: str
    reason: str
    report_token: Optional[str] = None
    bot_trap: Optional[str] = None  # Anti-Bot Honeypot

class StatusUpdateRequest(BaseModel):
    status: str

class VoiceQueryRequest(BaseModel):
    query_text: str
    report_id: Optional[str] = None
    bot_trap: Optional[str] = None  # Anti-Bot Honeypot

# Endpoints

@app.post("/api/analyze-report")
async def analyze_report(
    file: UploadFile = File(...),
    patient_name: str = Form("Anonymous Patient"),
    report_notes: Optional[str] = Form(None),
    bot_trap: Optional[str] = Form(None)  # Anti-Bot Honeypot
):
    # Verify no automated bot filled the invisible honeypot field
    verify_honeypot(bot_trap)

    try:
        content = await file.read()
        filename = file.filename or "uploaded_report.pdf"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as f:
            f.write(content)

        # AI analysis with medical safety guardrails
        analysis = await gemini_analyzer.analyze_document(
            file_bytes=content,
            filename=filename,
            mime_type=file.content_type or "application/octet-stream"
        )

        # Store record
        report_data = {
            "patient_name": patient_name,
            "filename": filename,
            "file_path": file_path,
            "report_notes": report_notes,
            "analysis": analysis,
            "doctor_notes": []
        }
        report_id = records_store.save_report(report_data)
        saved_record = records_store.get_report(report_id)

        return {
            "success": True,
            "report_id": report_id,
            "token": saved_record.get("token"),
            "qr_url": f"/api/qr/{saved_record.get('token')}",
            "record": saved_record
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report analysis failed: {str(e)}")

@app.post("/api/sample-report")
async def inject_sample_report(sample_type: str = "cbc", patient_name: str = "Sarah Connor"):
    sample_texts = {
        "cbc": """COMPLETE BLOOD COUNT (CBC) & HEMATOLOGY PANEL
Patient: Sarah Connor | Age: 34 | Sex: Female
Date: 2026-11-03 | Lab Ref: LAB-77291
Parameter          Observed Value    Reference Interval    Status
Hemoglobin         11.4 g/dL         12.0 - 15.5 g/dL      Low
RBC Count          4.1 mil/µL        4.0 - 5.2 mil/µL      Normal
WBC Total          7.8 x10^3/µL      4.5 - 11.0 x10^3/µL   Normal
Platelet Count     220 x10^3/µL      150 - 450 x10^3/µL    Normal
Hematocrit         35.2 %            36.0 - 46.0 %         Low
MCV                82.0 fL           80.0 - 100.0 fL       Normal
Remarks: Specimen satisfactory. Routine wellness evaluation.""",

        "lipid": """COMPREHENSIVE LIPID PROFILE
Patient: David Miller | Age: 48 | Sex: Male
Date: 2026-11-03 | Lab Ref: LIP-99021
Parameter          Observed Value    Reference Interval    Status
Total Cholesterol  218 mg/dL         125 - 200 mg/dL       High
HDL Cholesterol    44 mg/dL          40 - 60 mg/dL         Normal
LDL Cholesterol    132 mg/dL         50 - 100 mg/dL        High
Triglycerides      185 mg/dL         50 - 150 mg/dL        High
VLDL               36 mg/dL          5 - 30 mg/dL          Borderline High
Remarks: Fasting 12 hours noted.""",

        "metabolic": """METABOLIC & GLUCOSE PANEL
Patient: Anita Roy | Age: 42 | Sex: Female
Date: 2026-11-03 | Lab Ref: MET-55102
Parameter          Observed Value    Reference Interval    Status
Fasting Glucose    108 mg/dL         70 - 99 mg/dL         High
HbA1c              5.8 %             4.0 - 5.6 %           Borderline High
Creatinine         0.85 mg/dL        0.6 - 1.2 mg/dL       Normal
Blood Urea (BUN)   14.0 mg/dL        7 - 20 mg/dL          Normal
Remarks: Patient asymptomatic, routine annual screen."""
    }

    raw_text = sample_texts.get(sample_type, sample_texts["cbc"])
    analysis = gemini_analyzer._intelligent_fallback_analyzer(raw_text, f"Sample_{sample_type.upper()}_Report.txt")

    report_data = {
        "patient_name": patient_name,
        "filename": f"Sample_{sample_type.upper()}_Report.txt",
        "file_path": None,
        "report_notes": f"Auto-generated {sample_type.upper()} clinical laboratory test for demonstration",
        "analysis": analysis,
        "doctor_notes": []
    }
    report_id = records_store.save_report(report_data)
    saved = records_store.get_report(report_id)

    return {
        "success": True,
        "report_id": report_id,
        "token": saved.get("token"),
        "qr_url": f"/api/qr/{saved.get('token')}",
        "record": saved
    }

@app.get("/api/reports")
async def list_reports(patient_name: Optional[str] = None):
    return records_store.list_reports(patient_name)

@app.get("/api/reports/{id_or_token}")
async def get_report_by_token_or_id(id_or_token: str):
    record = records_store.get_report_by_token(id_or_token)
    if not record:
        record = records_store.get_report(id_or_token)
    if not record:
        raise HTTPException(status_code=404, detail="Medical report not found with provided ID or QR Token")
    return record

@app.get("/api/qr/{token}")
async def get_qr_image(token: str):
    qr_bytes = records_store.generate_qr_code(token)
    return Response(content=qr_bytes, media_type="image/png")

@app.post("/api/reports/{report_id}/notes")
async def add_doctor_notes(report_id: str, req: DoctorNotesRequest):
    success = records_store.add_doctor_notes(report_id, req.doctor_name, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Doctor notes attached successfully", "report": records_store.get_report(report_id)}

@app.get("/api/doctors")
async def list_doctors():
    return records_store.get_doctors()

@app.post("/api/appointments")
async def book_appointment(req: AppointmentRequest):
    # Verify no automated bot filled the invisible honeypot field
    verify_honeypot(req.bot_trap)

    doctor = records_store.get_doctor_by_id(req.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Selected doctor not found")
    
    appt = records_store.book_appointment({
        "patient_name": req.patient_name,
        "patient_phone": req.patient_phone,
        "doctor_id": req.doctor_id,
        "doctor_name": doctor["name"],
        "doctor_specialty": doctor["specialty"],
        "hospital": doctor["hospital"],
        "date": req.date,
        "time": req.time,
        "reason": req.reason,
        "report_token": req.report_token
    })
    return {"message": "Appointment scheduled successfully", "appointment": appt}

@app.get("/api/appointments")
async def list_appointments(doctor_id: Optional[str] = None, patient_name: Optional[str] = None):
    return records_store.list_appointments(doctor_id, patient_name)

@app.post("/api/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, req: StatusUpdateRequest):
    success = records_store.update_appointment_status(appt_id, req.status)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": f"Appointment status updated to {req.status}"}

@app.post("/api/voice/query")
async def process_voice_query(req: VoiceQueryRequest):
    verify_honeypot(req.bot_trap)
    report_context = None
    if req.report_id:
        record = records_store.get_report(req.report_id) or records_store.get_report_by_token(req.report_id)
        if record:
            report_context = record.get("analysis")
    
    result = await voice_pipeline.process_voice_query(req.query_text, report_context)
    return result

# Serve Web Frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "MediSync Hospital API active. Static dashboard loading..."}
