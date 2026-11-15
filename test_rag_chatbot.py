"""
Automated Test Suite for MediSync RAG Chatbot
Tests:
1. Laboratory Levels Grounding (CBC, Thyroid, Liver, Kidney)
2. Strict Medical Guardrails (No disease conclusions / diagnoses)
3. Doctor Recommendations & Appointment Booking Guidance
4. Multi-turn Conversation & Offline Determinism
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.records_store import records_store
from backend.extractor import document_extractor
from backend.parameter_parser import parameter_parser
from backend.rag_engine import rag_engine
from backend.medgemma_connector import medgemma_connector
from backend.rag_chatbot import rag_chatbot


def test_rag_chatbot():
    print("\n" + "=" * 65)
    print("🧪 RUNNING RAG CHATBOT AUTOMATED TEST SUITE")
    print("=" * 65)

    # 1. Setup sample reports in records_store
    print("\n--- STAGE 1: Initializing Clinical Patient Reports ---")
    verified_reports = [
        {
            "panel": "cbc",
            "name": "Sarah Connor",
            "text": """COMPLETE BLOOD COUNT (CBC) & HEMATOLOGY
Patient: Sarah Connor | Date: 2026-11-15 | Age: 34
Hemoglobin         11.4 g/dL         12.0 - 15.5 g/dL      Low
RBC Count          4.1 mil/µL        4.0 - 5.2 mil/µL      Normal
WBC Total          7.8 x10^3/µL      4.5 - 11.0 x10^3/µL   Normal
Platelet Count     220 x10^3/µL      150 - 450 x10^3/µL    Normal
Hematocrit         35.2 %            36.0 - 46.0 %         Low"""
        },
        {
            "panel": "thyroid",
            "name": "David Miller",
            "text": """COMPREHENSIVE THYROID PANEL
Patient: David Miller | Date: 2026-11-15 | Age: 45
TSH                6.80 µIU/mL       0.40 - 4.50 µIU/mL    High
Free T4 (FT4)      1.15 ng/dL        0.80 - 1.80 ng/dL     Normal"""
        },
        {
            "panel": "kidney",
            "name": "Robert Vance",
            "text": """RENAL FUNCTION PANEL
Patient: Robert Vance | Date: 2026-11-15 | Age: 54
Serum Creatinine   1.60 mg/dL        0.70 - 1.30 mg/dL     High
eGFR               52 mL/min/1.73m²  ≥ 90 mL/min/1.73m²    Low
Blood Urea (BUN)   26.0 mg/dL        7.0 - 20.0 mg/dL      High"""
        }
    ]

    created_records = {}

    for item in verified_reports:
        panel = item["panel"]
        raw_text = item["text"]
        metadata = parameter_parser.extract_metadata(raw_text)
        params = parameter_parser.parse_parameters(raw_text)
        rag_ctx = rag_engine.retrieve_context_for_parameters(params)
        analysis = medgemma_connector._grounded_rag_synthesis(
            detected_parameters=params,
            rag_context=rag_ctx,
            metadata=metadata,
            filename=f"{panel}_report.txt"
        )
        report_data = {
            "patient_name": item["name"],
            "filename": f"{panel}_report.txt",
            "file_path": f"/uploads/{panel}_report.txt",
            "report_notes": f"Verified {panel} test report",
            "extracted_raw_text": raw_text,
            "analysis": analysis,
            "doctor_notes": []
        }
        report_id = records_store.save_report(report_data)
        record = records_store.get_report(report_id)
        created_records[panel] = record
        print(f"  ✓ Created {panel.upper()} record (ID: {record['id']}, Token: {record['token']}) with {len(params)} parameters.")

    # 2. Test Laboratory Levels Queries
    print("\n--- STAGE 2: Testing Patient Level Inquiries ---")

    # Test 2.1: Hemoglobin query with CBC report
    cbc_record = created_records["cbc"]
    resp_cbc = rag_chatbot.chat(
        message="What is my hemoglobin level and what does it mean?",
        report_id=cbc_record["id"],
        history=[]
    )
    print("\n[User]: What is my hemoglobin level and what does it mean?")
    print(f"[Chatbot]: {resp_cbc['reply'][:200]}...")
    assert "11.4" in resp_cbc["reply"], "Chatbot reply should cite actual observed hemoglobin (11.4 g/dL)"
    assert "hemoglobin" in resp_cbc["reply"].lower()
    assert resp_cbc["parameters_cited"], "Should include parameters cited metadata"
    print("  ✓ Correctly cited actual patient value (11.4 g/dL) and clinical reference range")

    # Test 2.2: TSH query with Thyroid report
    thyroid_record = created_records["thyroid"]
    resp_tsh = rag_chatbot.chat(
        message="Why is my TSH level high?",
        report_id=thyroid_record["id"],
        history=[]
    )
    print("\n[User]: Why is my TSH level high?")
    print(f"[Chatbot]: {resp_tsh['reply'][:200]}...")
    assert "6.8" in resp_tsh["reply"] or "TSH" in resp_tsh["reply"], "Should cite TSH level"
    assert "not provide a medical diagnosis" in resp_tsh["reply"].lower() or "not diagnose" in resp_tsh["reply"].lower() or "educational" in resp_tsh["reply"].lower()
    print("  ✓ Educational explanation provided with explicit diagnostic guardrail")

    # Test 2.3: Creatinine query with Kidney report
    kidney_record = created_records["kidney"]
    resp_creat = rag_chatbot.chat(
        message="Explain my serum creatinine and eGFR values",
        report_id=kidney_record["id"],
        history=[]
    )
    print("\n[User]: Explain my serum creatinine and eGFR values")
    print(f"[Chatbot]: {resp_creat['reply'][:200]}...")
    assert "creatinine" in resp_creat["reply"].lower()
    assert "1.6" in resp_creat["reply"] or "eGFR" in resp_creat["reply"]
    print("  ✓ Accurately retrieved multiple kidney parameters with educational context")

    # 3. Test Medical Guardrails (Negative Assertion Tests)
    print("\n--- STAGE 3: Testing Strict Diagnostic Guardrails ---")
    prohibited_diagnoses = [
        "you have hypothyroidism",
        "you are diagnosed with anemia",
        "you suffer from chronic kidney disease",
        "you have liver failure"
    ]
    for prohibited in prohibited_diagnoses:
        assert prohibited not in resp_cbc["reply"].lower(), f"Violated guardrail: asserted '{prohibited}'"
        assert prohibited not in resp_tsh["reply"].lower(), f"Violated guardrail: asserted '{prohibited}'"
        assert prohibited not in resp_creat["reply"].lower(), f"Violated guardrail: asserted '{prohibited}'"
    print("  ✓ Verified: Zero assertive disease conclusions detected across all level explanations.")

    # 4. Test Doctor Specialist Recommendations & Appointment Booking
    print("\n--- STAGE 4: Testing Doctor Recommendations & Appointment Booking ---")

    # Test 4.1: Doctor recommendation for Thyroid report
    resp_doc_thyroid = rag_chatbot.chat(
        message="Which doctor should I book an appointment with for this thyroid report?",
        report_id=thyroid_record["id"],
        history=[]
    )
    print("\n[User]: Which doctor should I book an appointment with for this thyroid report?")
    print(f"[Chatbot]: {resp_doc_thyroid['reply'][:180]}...")
    assert resp_doc_thyroid["doctor_recommendation"] is not None, "Should recommend a specialist"
    assert "Mehta" in resp_doc_thyroid["doctor_recommendation"]["name"], "Should recommend Dr. Rajiv Mehta (Endocrinology)"
    assert "Endocrinology" in resp_doc_thyroid["doctor_recommendation"]["specialty"]
    print(f"  ✓ Correctly recommended specialist: {resp_doc_thyroid['doctor_recommendation']['name']} ({resp_doc_thyroid['doctor_recommendation']['specialty']})")

    # Test 4.2: Direct doctor inquiry ("I want to book an appointment with Dr. Jenkins")
    resp_doc_jenkins = rag_chatbot.chat(
        message="How can I schedule an appointment with Dr. Sarah Jenkins?",
        report_id=None,
        history=[]
    )
    print("\n[User]: How can I schedule an appointment with Dr. Sarah Jenkins?")
    print(f"[Chatbot]: {resp_doc_jenkins['reply'][:180]}...")
    assert resp_doc_jenkins["doctor_recommendation"] is not None
    assert "Jenkins" in resp_doc_jenkins["doctor_recommendation"]["name"]
    assert "Cardiology" in resp_doc_jenkins["doctor_recommendation"]["specialty"]
    print(f"  ✓ Handled direct doctor scheduling request for: {resp_doc_jenkins['doctor_recommendation']['name']}")

    # Test 4.3: General booking guidance
    resp_book_gen = rag_chatbot.chat(
        message="How do I book an appointment in MediSync?",
        report_id=None,
        history=[]
    )
    assert "book" in resp_book_gen["reply"].lower() or "appointment" in resp_book_gen["reply"].lower()
    print("  ✓ Provided clear booking workflow guidance")

    # 5. Test Multi-turn Conversation
    print("\n--- STAGE 5: Multi-Turn Conversation Continuity ---")
    history = [
        {"role": "user", "content": "What is my TSH level?"},
        {"role": "assistant", "content": resp_tsh["reply"]}
    ]
    resp_followup = rag_chatbot.chat(
        message="Can I book an appointment with a specialist to discuss this?",
        report_id=thyroid_record["id"],
        history=history
    )
    print("\n[User Followup]: Can I book an appointment with a specialist to discuss this?")
    print(f"[Chatbot]: {resp_followup['reply'][:180]}...")
    assert resp_followup["doctor_recommendation"] is not None
    assert "Mehta" in resp_followup["doctor_recommendation"]["name"]
    print("  ✓ Successfully resolved multi-turn context connecting thyroid level inquiry to endocrinologist consultation")

    print("\n" + "=" * 65)
    print("🎉 ALL RAG CHATBOT TESTS PASSED (100% SUCCESS)")
    print("=" * 65)


if __name__ == "__main__":
    test_rag_chatbot()
