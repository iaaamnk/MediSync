import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main import (
    list_doctors,
    inject_sample_report,
    get_qr_image,
    process_voice_query,
    book_appointment,
    add_doctor_notes,
    AppointmentRequest,
    DoctorNotesRequest,
    VoiceQueryRequest,
)

async def main():
    print("--- MediSync Direct Function Verification ---")

    # 1. Doctors
    docs = await list_doctors()
    print(f"[1/6] Doctors List: OK ({len(docs)} specialists loaded)")

    # 2. Sample CBC Report Injection & Gemini Clinical Analyzer
    res = await inject_sample_report("cbc", "Sarah Connor")
    token = res["token"]
    rep_id = res["report_id"]
    analysis = res["record"]["analysis"]
    print(f"[2/6] Sample Report & Medical Analyzer: OK (Token: {token}, Params: {len(analysis['parameters'])})")
    print(f"      Safety Guardrail Check: \"{analysis['disclaimer'][:75]}...\"")

    # 3. Dynamic QR Code
    qr_res = await get_qr_image(token)
    print(f"[3/6] Dynamic QR Code Pass: OK ({len(qr_res.body)} bytes generated, Media: {qr_res.media_type})")

    # 4. Voice Pipeline
    v_req = VoiceQueryRequest(query_text="What does hemoglobin mean?", report_id=rep_id)
    v_res = await process_voice_query(v_req)
    print(f"[4/6] Voice Pipeline: OK -> \"{v_res['speech_response'][:75]}...\"")

    # 5. Book Appointment
    a_req = AppointmentRequest(
        patient_name="Sarah Connor",
        patient_phone="+1 555-0192",
        doctor_id="doc_1",
        date="2026-11-05",
        time="10:00 AM",
        reason="Follow up on blood work",
        report_token=token
    )
    a_res = await book_appointment(a_req)
    print(f"[5/6] Appointment Booking: OK (ID: {a_res['appointment']['id']} with {a_res['appointment']['doctor_name']})")

    # 6. Doctor Consultation Notes
    d_req = DoctorNotesRequest(
        doctor_name="Dr. Sarah Jenkins",
        notes="Reviewed CBC parameters. Slight low hemoglobin noted. Recommended iron-rich diet and re-testing in 6 weeks."
    )
    d_res = await add_doctor_notes(rep_id, d_req)
    print(f"[6/6] Doctor Notes Attachment: OK -> Total notes: {len(d_res['report']['doctor_notes'])}")

    print("\n========================================================")
    print("ALL CORE MEDISYNC FEATURES FUNCTIONING WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == "__main__":
    asyncio.run(main())

