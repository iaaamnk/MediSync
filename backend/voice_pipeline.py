import os
import json
import httpx
from typing import Dict, Any, Optional
from backend.rag_engine import rag_engine

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

VOICE_SYSTEM_PROMPT = """
You are MediSync Voice Assistant, an evidence-based clinical laboratory guide.
CRITICAL MEDICAL SAFETY:
- You must NOT diagnose diseases, label conditions, or declare medical verdicts.
- Use the retrieved medical knowledge context to answer questions about lab terms, reference intervals, biological variations (hydration, exercise, fasting), and appointment preparation.
- Keep answers warm, concise, and optimized for spoken delivery (2 to 4 sentences).
- Always recommend discussing findings with the attending physician.
"""

class VoicePipeline:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    async def process_voice_query(self, query_text: str, report_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes voice query text using RAG retrieval + AI synthesis.
        """
        # 1. Retrieve supporting context from knowledge base
        rag_chunks = rag_engine.search_knowledge(query_text, top_k=2)
        rag_context_str = "\n".join([f"KB Resource ({c.get('title')}): {c.get('content')}" for c in rag_chunks])

        # 2. Add current report context if available
        context_str = ""
        if report_context:
            title = report_context.get("report_title", "Medical Report")
            params = [f"{p.get('name')}: {p.get('value')} ({p.get('status')})" for p in report_context.get("parameters", [])[:6]]
            context_str = f"\nPatient Active Lab Data: {title}\nKey observed parameters: {', '.join(params)}"

        full_prompt = (
            f"User Voice Question: '{query_text}'\n"
            f"{context_str}\n"
            f"Verified Medical Knowledge Base Reference:\n{rag_context_str}\n\n"
            f"Provide a gentle, 2-3 sentence spoken explanation. Never diagnose any illness."
        )

        # 3. Model call if API key present
        if self.api_key:
            try:
                payload = {
                    "system_instruction": {"parts": [{"text": VOICE_SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.25, "maxOutputTokens": 220}
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{GEMINI_API_URL}?key={self.api_key}",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            return {
                                "transcript": query_text,
                                "speech_response": answer,
                                "source": "Gemini-RAG Voice Pipeline"
                            }
            except Exception as e:
                print(f"Voice API error: {e}")

        # 4. Deterministic RAG Fallback using retrieved medical knowledge chunks
        lower_q = query_text.lower()
        if rag_chunks:
            top_chunk = rag_chunks[0]
            title = top_chunk.get("title", "")
            content = top_chunk.get("content", "")
            # Synthesize clean 2-sentence spoken output
            resp = f"{title} is evaluated as part of routine laboratory health assessments. {content[:180]}... Remember that numbers reflect general physiology rather than a disease, so your physician will interpret them in context."
        elif "appointment" in lower_q or "doctor" in lower_q:
            resp = "You can schedule a consultation with our specialists in Cardiology, Endocrinology, General Medicine, or Pulmonology using the Book Appointment tab."
        else:
            resp = f"Regarding '{query_text}', laboratory parameters reflect normal physiological variations influenced by hydration, timing, and diet. Please consult your physician for individualized medical interpretation."

        return {
            "transcript": query_text,
            "speech_response": resp,
            "source": "MediSync Clinical RAG Engine"
        }

voice_pipeline = VoicePipeline()
