import os
import json
import httpx
from typing import Dict, Any, Optional

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

VOICE_SYSTEM_PROMPT = """
You are MediSync Voice Assistant, a gentle, informative medical guide.
CRITICAL MEDICAL SAFETY:
- You must NOT diagnose diseases or conclude medical conditions.
- You answer questions about medical terms, lab report values, appointment preparation, and health education.
- Keep your answers concise, warm, easy to listen to when read aloud (2 to 4 sentences).
- If asked "Do I have cancer/diabetes/etc?", clarify that laboratory markers only indicate levels, not diseases, and advise checking with their doctor.
"""

class VoicePipeline:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    async def process_voice_query(self, query_text: str, report_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes voice query text and returns intelligent, spoken-friendly answer.
        """
        context_str = ""
        if report_context:
            title = report_context.get("report_title", "Medical Report")
            params = [f"{p['name']}: {p['value']} ({p['status']})" for p in report_context.get("parameters", [])[:6]]
            context_str = f"\nRelevant Patient Report: {title}\nKey parameters: {', '.join(params)}"

        if self.api_key:
            try:
                payload = {
                    "system_instruction": {
                        "parts": [{"text": VOICE_SYSTEM_PROMPT}]
                    },
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"Patient/Doctor voice query: '{query_text}'{context_str}\nProvide a helpful, spoken explanation without diagnosing any disease."}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 250
                    }
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        f"{GEMINI_API_URL}?key={self.api_key}",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            return {
                                "transcript": query_text,
                                "speech_response": answer.strip(),
                                "source": "Gemini-2.5-Flash"
                            }
            except Exception as e:
                print(f"Voice Gemini API error: {e}")

        # Intelligent fallback voice assistant
        lower_q = query_text.lower()
        if "hemoglobin" in lower_q:
            resp = "Hemoglobin is the protein in your red blood cells carrying oxygen. Levels can fluctuate based on hydration, altitude, and diet. It does not diagnose any illness on its own, so do share this with your doctor."
        elif "wbc" in lower_q or "white blood" in lower_q:
            resp = "White blood cells defend your body against bacteria and viruses. A mild elevation can happen naturally during stress or routine recovery. Your doctor can review this in full context."
        elif "glucose" in lower_q or "sugar" in lower_q:
            resp = "Blood glucose measures current circulating sugar. Fasting status significantly influences these readings. Be sure to inform your doctor if you had fasted before the sample."
        elif "cholesterol" in lower_q or "lipid" in lower_q:
            resp = "Cholesterol is vital for your cells and hormones. Having higher or lower levels is a routine wellness marker to discuss regarding balanced nutrition and exercise."
        elif "appointment" in lower_q or "doctor" in lower_q:
            resp = "You can book an appointment with our specialists in Cardiology, Endocrinology, General Medicine, or Pulmonology using the Appointments tab right here."
        else:
            resp = f"Thank you for your question. Regarding '{query_text}', remember that laboratory numbers are general indicators rather than disease diagnoses. Please consult your physician for individualized medical advice."

        return {
            "transcript": query_text,
            "speech_response": resp,
            "source": "MediSync Voice Engine"
        }

voice_pipeline = VoicePipeline()

