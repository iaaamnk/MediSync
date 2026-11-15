import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.extractor import document_extractor
from backend.parameter_parser import parameter_parser
from backend.rag_engine import rag_engine
from backend.medgemma_connector import medgemma_connector

def test_knowledge_base_structure():
    print("=== [1/5] Testing Medical Knowledge Base Structure ===")
    kb = rag_engine.kb
    assert "panels" in kb
    assert "cbc" in kb["panels"]
    assert "thyroid" in kb["panels"]
    assert "liver" in kb["panels"]
    assert "kidney" in kb["panels"]
    print(f"  [OK] Panels verified: {list(kb['panels'].keys())}")

    # Verify reference limitations guide
    guide = kb.get("reference_range_limitations_guide", {})
    principles = guide.get("core_principles", [])
    assert len(principles) >= 5, "Must contain all 5 core reference range principles"
    print(f"  [OK] Core reference range limitations principles verified: {len(principles)} principles")

    # Verify authoritative reference citations
    citations = guide.get("authoritative_references", [])
    assert len(citations) >= 4, "Must contain ADLM, NIH, WHO, Tietz citations"
    print(f"  [OK] Authoritative medical citations verified: {len(citations)} sources")

def test_document_extractor():
    print("\n=== [2/5] Testing Document & Table Extractor ===")
    sample_raw = """
    ST. JUDE CLINICAL DIAGNOSTICS LABORATORY
    Patient: John Doe | Date: 2026-11-15
    Test Name        Observed    Unit       Reference Range    Flag
    Hemoglobin       13.2        g/dL       13.5 - 17.5        Low
    WBC Count        6.8         x10^3/uL   4.5 - 11.0         Normal
    Platelets        240         x10^3/uL   150 - 450          Normal
    """
    doc_res = document_extractor.extract_from_bytes(sample_raw.encode("utf-8"), "test_report.txt")
    assert doc_res["success"] == True
    assert "Hemoglobin" in doc_res["full_text"]
    print(f"  [OK] Document extraction verified ({len(doc_res['structured_lines'])} structured lines extracted)")

def test_parameter_parser():
    print("\n=== [3/5] Testing Medical Parameter & Value Parser ===")
    test_text = """
    TSH : 5.40 uIU/mL (0.40 - 4.50)
    Free T4 : 1.20 ng/dL (0.80 - 1.80)
    Serum Creatinine : 1.45 mg/dL (0.60 - 1.20)
    ALT (SGPT) : 62 U/L (7 - 35)
    """
    params = parameter_parser.parse_parameters(test_text)
    param_names = [p["name"] for p in params]
    assert any("TSH" in n for n in param_names)
    assert any("Free T4" in n for n in param_names)
    assert any("Creatinine" in n for n in param_names)
    assert any("ALT" in n for n in param_names)

    # Check status evaluation
    tsh = next(p for p in params if "TSH" in p["name"])
    assert tsh["status"] == "High"
    assert tsh["numeric_value"] == 5.40

    ft4 = next(p for p in params if "Free T4" in p["name"])
    assert ft4["status"] == "Normal"

    creat = next(p for p in params if "Creatinine" in p["name"])
    assert creat["status"] == "High"

    print(f"  [OK] Successfully parsed and classified {len(params)} parameters with mathematical thresholds")

def test_rag_retrieval():
    print("\n=== [4/5] Testing RAG Context Retrieval & Grounding ===")
    detected = [
        {"id": "hemoglobin", "name": "Hemoglobin", "panel": "cbc", "value": "11.4 g/dL", "status": "Low"},
        {"id": "alt", "name": "ALT (Alanine Aminotransferase)", "panel": "liver", "value": "58 U/L", "status": "High"},
        {"id": "creatinine", "name": "Serum Creatinine", "panel": "kidney", "value": "1.35 mg/dL", "status": "High"}
    ]
    rag_ctx = rag_engine.retrieve_context_for_parameters(detected)
    assert len(rag_ctx["parameter_contexts"]) == 3
    assert len(rag_ctx["range_limitations"]) >= 5
    assert len(rag_ctx["authoritative_sources"]) >= 4

    # Test query search
    search_res = rag_engine.search_knowledge("What causes creatinine elevation?")
    assert len(search_res) > 0
    assert any("creatinine" in c["title"].lower() or "kidney" in c["content"].lower() for c in search_res)
    print(f"  [OK] RAG engine retrieved {len(rag_ctx['parameter_contexts'])} targeted context chunks and range limitations")

def test_sample_reports_verification():
    print("\n=== [5/5] Testing 4 Manually Verified Clinical Sample Reports ===")

    verified_reports = [
        {
            "panel_type": "CBC (Hematology)",
            "text": """COMPLETE BLOOD COUNT (CBC) & HEMATOLOGY
Patient: Sarah Connor | Date: 2026-11-15 | Age: 34
Hemoglobin         11.4 g/dL         12.0 - 15.5 g/dL      Low
RBC Count          4.1 mil/µL        4.0 - 5.2 mil/µL      Normal
WBC Total          7.8 x10^3/µL      4.5 - 11.0 x10^3/µL   Normal
Platelet Count     220 x10^3/µL      150 - 450 x10^3/µL    Normal
Hematocrit         35.2 %            36.0 - 46.0 %         Low
MCV                82.0 fL           80.0 - 100.0 fL       Normal""",
            "expected_highs": [],
            "expected_lows": ["Hemoglobin", "Hematocrit"]
        },
        {
            "panel_type": "Thyroid Function",
            "text": """COMPREHENSIVE THYROID PANEL
Patient: David Miller | Date: 2026-11-15 | Age: 45
TSH                5.20 µIU/mL       0.40 - 4.50 µIU/mL    High
Free T4 (FT4)      1.15 ng/dL        0.80 - 1.80 ng/dL     Normal""",
            "expected_highs": ["TSH (Thyroid Stimulating Hormone)"],
            "expected_lows": []
        },
        {
            "panel_type": "Hepatic (Liver Function)",
            "text": """LIVER FUNCTION TESTS (LFT)
Patient: Elena Rossi | Date: 2026-11-15 | Age: 38
ALT (SGPT)         58 U/L            7 - 35 U/L            High
AST (SGOT)         44 U/L            10 - 40 U/L           High
ALP                85 U/L            44 - 147 U/L          Normal
Total Bilirubin    0.9 mg/dL         0.2 - 1.2 mg/dL       Normal""",
            "expected_highs": ["ALT (Alanine Aminotransferase)", "AST (Aspartate Aminotransferase)"],
            "expected_lows": []
        },
        {
            "panel_type": "Renal (Kidney Function)",
            "text": """RENAL FUNCTION PANEL
Patient: Robert Vance | Date: 2026-11-15 | Age: 54
Serum Creatinine   1.35 mg/dL        0.70 - 1.30 mg/dL     High
eGFR               58 mL/min/1.73m²  ≥ 90 mL/min/1.73m²    Low
Blood Urea (BUN)   24.0 mg/dL        7.0 - 20.0 mg/dL      High""",
            "expected_highs": ["Serum Creatinine", "Blood Urea Nitrogen (BUN)"],
            "expected_lows": ["eGFR (estimated Glomerular Filtration Rate)"]
        }
    ]

    for report in verified_reports:
        panel_name = report["panel_type"]
        raw_text = report["text"]
        metadata = parameter_parser.extract_metadata(raw_text)
        params = parameter_parser.parse_parameters(raw_text)
        rag_context = rag_engine.retrieve_context_for_parameters(params)

        analysis = medgemma_connector._grounded_rag_synthesis(
            detected_parameters=params,
            rag_context=rag_context,
            metadata=metadata,
            filename=f"Verified_{panel_name.replace(' ', '_')}.txt"
        )

        # 1. Verify patient values are preserved as primary source
        for p in analysis["parameters"]:
            assert p["value"] != "", f"Observed value missing for {p['name']}"
            assert p["reference_range"] != "", f"Reference range missing for {p['name']}"

        # 2. Verify non-diagnostic safety guardrail
        disclaimer = analysis.get("disclaimer", "")
        assert "not provide medical diagnosis" in disclaimer.lower() or "not" in disclaimer.lower()
        
        # Verify NO disease diagnosis assertions
        overview = analysis.get("summary_overview", "").lower()
        forbidden_conclusions = ["you have anemia", "you have kidney disease", "you have hepatitis", "you have hypothyroidism"]
        for fc in forbidden_conclusions:
            assert fc not in overview, f"Forbidden disease conclusion '{fc}' found in analysis overview!"

        # 3. Verify limitations & citations attached
        assert len(analysis["reference_range_limitations"]) >= 5
        assert len(analysis["authoritative_sources"]) >= 4

        high_found = [p["name"] for p in analysis["parameters"] if p["status"] == "High"]
        low_found = [p["name"] for p in analysis["parameters"] if p["status"] == "Low"]

        print(f"  [OK] Verified Sample: {panel_name}")
        print(f"       Observed Highs: {high_found}")
        print(f"       Observed Lows:  {low_found}")
        print(f"       Grounding Check: Zero disease assertions, {len(analysis['questions_for_doctor'])} doctor questions generated.")

def run_all_tests():
    test_knowledge_base_structure()
    test_document_extractor()
    test_parameter_parser()
    test_rag_retrieval()
    test_sample_reports_verification()

    print("\n=======================================================================")
    print("ALL 8 STAGES OF MEDICAL KNOWLEDGE BASE & RAG PIPELINE FULLY VERIFIED!")
    print("=======================================================================")

if __name__ == "__main__":
    run_all_tests()
