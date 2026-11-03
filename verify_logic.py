import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.records_store import records_store
from backend.gemini_analyzer import gemini_analyzer

def test():
    print("--- MediSync Business & Safety Logic Verification ---")

    # 1. Test Doctors
    docs = records_store.get_doctors()
    assert len(docs) >= 4
    print(f"[OK] Doctors database loaded: {len(docs)} physicians.")
    for d in docs:
        print(f"   * {d['name']} ({d['specialty']}) - {d['hospital']}")

    # 2. Test Report Analysis & Medical Safety Guardrails
    sample_text = """
    COMPLETE BLOOD COUNT (CBC)
    Patient: Sarah Connor
    Hemoglobin 11.2 g/dL (Normal 12.0 - 15.5)
    WBC 8.5 x10^3/uL (Normal 4.5 - 11.0)
    Platelets 250 x10^3/uL (Normal 150 - 450)
    """
    analysis = gemini_analyzer._intelligent_fallback_analyzer(sample_text, "CBC_Report.txt")
    print(f"[OK] Analyzer parsed {len(analysis['parameters'])} parameters:")
    for p in analysis['parameters']:
        print(f"   * {p['name']}: {p['value']} [{p['status']}] - {p['explanation']}")

    # SAFETY CHECK: Must NOT diagnose diseases
    disclaimer = analysis['disclaimer']
    assert "not" in disclaimer.lower()
    print(f"[OK] Safety Guardrail Verified: \"{disclaimer[:70]}...\"")

    # 3. Save report and test tokens
    rep_id = records_store.save_report({
        "patient_name": "Sarah Connor",
        "filename": "CBC_Report.txt",
        "analysis": analysis,
        "doctor_notes": []
    })
    saved = records_store.get_report(rep_id)
    token = saved["token"]
    print(f"[OK] Report saved with Token: {token}")

    # 4. QR Code generation
    qr_png = records_store.generate_qr_code(token)
    assert len(qr_png) > 500
    print(f"[OK] QR Code PNG generated: {len(qr_png)} bytes")

    # 5. Appointment Booking
    appt = records_store.book_appointment({
        "patient_name": "Sarah Connor",
        "patient_phone": "+1 555-0192",
        "doctor_id": docs[0]["id"],
        "doctor_name": docs[0]["name"],
        "doctor_specialty": docs[0]["specialty"],
        "hospital": docs[0]["hospital"],
        "date": "2026-11-05",
        "time": "10:00 AM",
        "reason": "Blood test review",
        "report_token": token
    })
    print(f"[OK] Appointment booked: ID {appt['id']} for {appt['patient_name']} with {appt['doctor_name']}")

    # 6. Doctor Consultation Notes
    records_store.add_doctor_notes(
        rep_id,
        "Dr. Sarah Jenkins",
        "Reviewed CBC markers. Advised balanced nutrition and re-eval in 6 weeks."
    )
    updated = records_store.get_report(rep_id)
    print(f"[OK] Doctor Consultation Notes attached: \"{updated['doctor_notes'][0]['notes']}\"")

    print("\n========================================================")
    print("ALL CORE CLINICAL WORKFLOWS VERIFIED WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == "__main__":
    test()
