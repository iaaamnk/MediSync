# 🏥 MediSync — Intelligent Hospital Dashboard System

MediSync is a modern hospital dashboard system featuring **Patient Portal**, **Doctor Portal**, **Gemini-powered Medical Report Analyzer** (with strict non-diagnostic safety guardrails), **Dynamic QR Code Access**, an interactive **Voice Pipeline**, and an **Appointment Booking & Management System**.

Built with **FastAPI** (Python backend) and **Flutter** (Mobile/Web/Desktop frontend) with a high-fidelity web dashboard.

---

## 🛡️ Anti-Bot & Threat Protection System

MediSync incorporates multi-layered bot defenses:
1. **Malicious Bot & Scraper Inspection**:
   * Inspects incoming `User-Agent` headers and blocks known vulnerability scanners, scrapers, and bot frameworks (e.g. `sqlmap`, `nikto`, `masscan`, `scrapy`, `wpscan`, `gobuster`, etc.) with `403 Forbidden`.
   * Rejects empty or missing `User-Agent` requests on sensitive write/mutation routes.
2. **Dynamic Sliding-Window Rate Limiter**:
   * Per-IP sliding window throttle preventing automated DDoS, report flooding, and spam.
   * Throttles requests exceeding thresholds with `429 Too Many Requests` and a standard `Retry-After` header.
3. **Form Honeypot Traps**:
   * Invisible honeypot trap fields (`bot_trap`) integrated into report submission and appointment booking forms.
   * Hidden from human users via CSS/ARIA attributes; automated spambots that blindly fill all input fields are caught and immediately rejected (`400 Bad Request`).
4. **Client-Side Human Activity Verification**:
   * Lightweight human event listener tracking genuine user interaction (pointer movement, touch, keystrokes).
5. **Defensive Security Headers**:
   * `X-Content-Type-Options: nosniff`
   * `X-Frame-Options: DENY`
   * `X-XSS-Protection: 1; mode=block`
   * `Referrer-Policy: strict-origin-when-cross-origin`
   * `Permissions-Policy: geolocation=(), microphone=*, camera=*`
6. **Crawler Protection (`/robots.txt`)**:
   * Disallows search engine crawlers and automated bots from indexing `/api/`, `/uploads/`, or patient access tokens.

---

## 🔒 Gemini API Key Security

* **Zero Frontend Exposure**: The Gemini API key setting is completely removed from the UI and client-side code.
* The API key is securely loaded on the server via `.env` or system environment variable `GEMINI_API_KEY`.
* Copy `.env.example` to `.env` and insert your key:
  ```env
  GEMINI_API_KEY=your_actual_gemini_api_key_here
  ```
* If no key is set, MediSync automatically falls back to its built-in clinical rule engine for CBC, Lipid, and Metabolic panels.

---

## 🌟 Key Features

### 👤 1. Patient Portal
* **Medical Report Analyzer**:
  * Upload PDF lab reports or image scans (JPG/PNG).
  * Gemini multimodal AI extraction or fallback clinical parser.
  * **Critical Safety Directive**: The AI strictly **does NOT diagnose diseases or conclude conditions**. It provides objective parameter breakdowns, standard reference ranges, flagged indicators (Normal / High / Low), lifestyle wellness context, and suggested questions for the doctor.
  * 1-Click Clinical Sample Reports: Complete Blood Count (CBC), Comprehensive Lipid Profile, Metabolic & Glucose Panel.
* **Doctor QR Access Pass**:
  * Automatically generates a unique secure Report Token and high-resolution dynamic QR code (`/api/qr/{token}`).
  * Patients can show this QR code to the doctor during consultation for instant chart access.
* **Appointment Booking**:
  * Select specialist physicians (Cardiology, Endocrinology, Internal Medicine, Pulmonology).
  * Schedule date, time slot, reason for visit, and auto-link uploaded report tokens.
  * View upcoming and historical appointments with status tracking.
* **Interactive Voice Assistant (Voice Pipeline)**:
  * Speech recognition (Web Speech API) + Gemini voice processing + Speech Synthesis (audio playback).
  * Inquire verbally about lab terms (e.g., *"What does my hemoglobin level mean?"*, *"Why is fasting glucose important?"*).

---

### 🩺 2. Doctor Portal
* **QR Code Scanner & Access**:
  * Live camera QR code scanner (webcam / mobile camera) or direct token lookup.
  * Instantly loads the patient's analyzed chart, laboratory metrics, and raw document.
* **Attending Physician Clinical Notes**:
  * Doctors can author, sign, and append clinical consultation notes, prescriptions, and follow-up guidance directly to the patient's digital chart.
* **Consultations Queue & Schedule**:
  * View real-time appointments booked by patients.
  * Open attached reports directly with 1 click.
  * Update appointment status (`Confirmed` ➔ `In Consultation` ➔ `Completed`).

---

## 🚀 How to Run

### 1. Launch the FastAPI Server + Integrated Web Dashboard

```powershell
.\.python\python.exe start_server.py
```
*(Or with system Python: `python start_server.py`)*

* **Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Run the Flutter Frontend
```bash
cd flutter_frontend
flutter pub get
flutter run
```
