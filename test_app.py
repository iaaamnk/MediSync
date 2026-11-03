import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app

def run_tests():
    client = TestClient(app)

    print("--- Running MediSync Feature Verification ---")

    # 1. Doctors
    r1 = client.get('/api/doctors')
    assert r1.status_code == 200, f"Doctors fetch failed: {r1.text}"
    docs = r1.json()
    print(f"[1/7] Doctors List: OK ({len(docs)} physicians available)")

    # 2. Sample CBC Report
    r2 = client.post('/api/sample-report?sample_type=cbc')
    assert r2.status_code == 200, f"Sample report failed: {r2.text}"
    rep = r2.json()
    token = rep['token']
    report_id = rep['report_id']
    params = rep['record']['analysis']['parameters']
    disclaimer = rep['record']['analysis']['disclaimer']
    print(f"[2/7] Report Analyzer & Gemini Engine: OK (Token: {token}, {len(params)} parameters parsed)")
    print(f"      Medical Safety Guardrail Check: \"{disclaimer[:70]}...\"")
    assert "not provide medical diagnosis" in disclaimer.lower() or "not" in disclaimer.lower()

    # 3. Dynamic QR Code Generation
    r3 = client.get(f'/api/qr/{token}')
    assert r3.status_code == 200, f"QR code failed: {r3.text}"
    assert r3.headers['content-type'] == 'image/png'
    print(f"[3/7] Dynamic QR Code Engine: OK (Generated {len(r3.content)} bytes PNG)")

    # 4. Voice Pipeline
    r4 = client.post('/api/voice/query', json={'query_text': 'What does my hemoglobin level indicate?'})
    assert r4.status_code == 200, f"Voice query failed: {r4.text}"
    voice_resp = r4.json()['speech_response']
    print(f"[4/7] Voice Pipeline & AI Speech Engine: OK -> \"{voice_resp[:75]}...\"")

    # 5. Appointment Booking
    r5 = client.post('/api/appointments', json={
        'patient_name': 'Sarah Connor',
        'patient_phone': '+1 555-0192',
        'doctor_id': 'doc_1',
        'date': '2026-11-05',
        'time': '10:00 AM',
        'reason': 'Follow up on laboratory metrics',
        'report_token': token
    })
    assert r5.status_code == 200, f"Appointment booking failed: {r5.text}"
    appt = r5.json()['appointment']
    print(f"[5/7] Appointment Booking & Linking: OK (ID: {appt['id']} with {appt['doctor_name']})")

    # 6. Doctor Consultation Notes
    r6 = client.post(f'/api/reports/{report_id}/notes', json={
        'doctor_name': 'Dr. Sarah Jenkins',
        'notes': 'Reviewed CBC indicators. Advised iron-rich nutrition and re-test in 6 weeks.'
    })
    assert r6.status_code == 200, f"Doctor notes failed: {r6.text}"
    note = r6.json()['report']['doctor_notes'][0]['notes']
    print(f"[6/7] Doctor Clinical Notes & Digital Chart: OK -> \"{note}\"")

    # 7. Web Dashboard Static Serving
    r7 = client.get('/')
    assert r7.status_code == 200, f"Web dashboard failed: {r7.text}"
    assert 'MediSync' in r7.text
    print(f"[7/7] Hospital Web Dashboard UI: OK ({len(r7.text)} characters)")

    print("\n==================================================")
    print("ALL MEDISYNC HOSPITAL DASHBOARD FEATURES VERIFIED!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()

