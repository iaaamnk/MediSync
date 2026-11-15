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
from backend.extractor import document_extractor
from backend.parameter_parser import parameter_parser
from backend.rag_engine import rag_engine
from backend.medgemma_connector import medgemma_connector
from backend.voice_pipeline import voice_pipeline
from backend.rag_chatbot import rag_chatbot
from backend.security import inspect_request_for_bots, verify_honeypot

app = FastAPI(
    title="MediSync Hospital Dashboard API",
    description="Hospital Dashboard System with Patient Portal, Doctor Portal, MedGemma/Gemini RAG Medical Report Analyzer, QR Code Access, Voice Pipeline, and Appointment Booking.",
    version="2.0.0"
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

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    report_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None
    bot_trap: Optional[str] = None  # Anti-Bot Honeypot

# Endpoints

@app.post("/api/chat")
async def chat_with_rag(req: ChatRequest):
    """
    RAG-grounded conversational agent that answers inquiries regarding
    observed patient laboratory levels and hospital doctor appointment scheduling.
    """
    verify_honeypot(req.bot_trap)
    history_dicts = [{"role": h.role, "content": h.content} for h in req.history] if req.history else []
    result = await rag_chatbot.answer_chat(
        user_message=req.message,
        report_id=req.report_id,
        chat_history=history_dicts
    )
    return result

@app.get("/api/knowledge-base")
async def get_medical_knowledge_base():
    """
    Returns the structured medical knowledge base covering test descriptions,
    reference range limitations guide, and authoritative citations.
    """
    return rag_engine.kb

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

        # 1. Document Extraction (PDF & Image table/text parser)
        doc_data = document_extractor.extract_from_bytes(content, filename, file.content_type or "")
        extracted_text = doc_data.get("full_text", "")

        # 2. Extract Metadata & Lab Parameters
        metadata = parameter_parser.extract_metadata(extracted_text)
        if patient_name and patient_name != "Anonymous Patient":
            metadata["patient_name"] = patient_name

        detected_parameters = parameter_parser.parse_parameters(extracted_text)

        # 3. Retrieve Medical Knowledge Base Context via RAG Engine
        rag_context = rag_engine.retrieve_context_for_parameters(detected_parameters)

        # 4. Generate Grounded Structured Analysis via MedGemma Connector
        analysis = await medgemma_connector.generate_structured_analysis(
            extracted_text=extracted_text,
            detected_parameters=detected_parameters,
            rag_context=rag_context,
            metadata=metadata,
            filename=filename
        )

        # 5. Store Record in Database
        report_data = {
            "patient_name": metadata.get("patient_name") or patient_name,
            "filename": filename,
            "file_path": file_path,
            "report_notes": report_notes,
            "extracted_raw_text": extracted_text[:2000],
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
Date: 2026-11-15 | Lab Ref: LAB-77291
Parameter          Observed Value    Reference Interval    Status
Hemoglobin         11.4 g/dL         12.0 - 15.5 g/dL      Low
RBC Count          4.1 mil/µL        4.0 - 5.2 mil/µL      Normal
WBC Total          7.8 x10^3/µL      4.5 - 11.0 x10^3/µL   Normal
Platelet Count     220 x10^3/µL      150 - 450 x10^3/µL    Normal
Hematocrit         35.2 %            36.0 - 46.0 %         Low
MCV                82.0 fL           80.0 - 100.0 fL       Normal
Remarks: Specimen satisfactory. Routine wellness evaluation.""",

        "thyroid": """COMPREHENSIVE THYROID FUNCTION PROFILE
Patient: David Miller | Age: 45 | Sex: Male
Date: 2026-11-15 | Lab Ref: THY-88410
Parameter          Observed Value    Reference Interval    Status
TSH                5.20 µIU/mL       0.40 - 4.50 µIU/mL    High
Free T4 (FT4)      1.15 ng/dL        0.80 - 1.80 ng/dL     Normal
Remarks: Patient asymptomatic. Repeat TSH recommended in 6-8 weeks.""",

        "liver": """COMPREHENSIVE HEPATIC & LIVER FUNCTION PANEL
Patient: Elena Rossi | Age: 38 | Sex: Female
Date: 2026-11-15 | Lab Ref: LFT-33921
Parameter          Observed Value    Reference Interval    Status
ALT (SGPT)         58 U/L            7 - 35 U/L            High
AST (SGOT)         44 U/L            10 - 40 U/L           High
ALP                85 U/L            44 - 147 U/L          Normal
Total Bilirubin    0.9 mg/dL         0.2 - 1.2 mg/dL       Normal
Remarks: Recent strenuous physical training noted prior to blood draw.""",

        "kidney": """RENAL FUNCTION & METABOLIC PANEL
Patient: Robert Vance | Age: 54 | Sex: Male
Date: 2026-11-15 | Lab Ref: KFT-44109
Parameter          Observed Value    Reference Interval    Status
Serum Creatinine   1.35 mg/dL        0.70 - 1.30 mg/dL     High
eGFR               58 mL/min/1.73m²  ≥ 90 mL/min/1.73m²    Low
Blood Urea (BUN)   24.0 mg/dL        7.0 - 20.0 mg/dL      High
Uric Acid          6.8 mg/dL         3.5 - 7.2 mg/dL       Normal
Remarks: Patient active in weight training. Mild fluid restriction reported."""
    }

    raw_text = sample_texts.get(sample_type, sample_texts["cbc"])
    filename = f"Sample_{sample_type.upper()}_Report.txt"
    
    metadata = parameter_parser.extract_metadata(raw_text)
    metadata["patient_name"] = patient_name

    detected_parameters = parameter_parser.parse_parameters(raw_text)
    rag_context = rag_engine.retrieve_context_for_parameters(detected_parameters)
    analysis = await medgemma_connector.generate_structured_analysis(
        extracted_text=raw_text,
        detected_parameters=detected_parameters,
        rag_context=rag_context,
        metadata=metadata,
        filename=filename
    )

    report_data = {
        "patient_name": patient_name,
        "filename": filename,
        "file_path": None,
        "report_notes": f"Verified {sample_type.upper()} clinical laboratory test for demonstration",
        "extracted_raw_text": raw_text,
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
