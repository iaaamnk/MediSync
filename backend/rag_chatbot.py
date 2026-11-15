import os
import json
import re
import httpx
from typing import Dict, Any, List, Optional
from backend.records_store import records_store
from backend.rag_engine import rag_engine

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

RAG_CHATBOT_SYSTEM_PROMPT = """You are MediSync Clinical & Appointment Assistant, an expert, empathetic hospital AI guide.
Your dual mission is:
1. Explain patient laboratory levels accurately using the patient's own test report and verified medical knowledge.
2. Guide patients on scheduling and booking consultations with the appropriate specialist doctor in our hospital.

CRITICAL MEDICAL SAFETY & ETHICAL RULES:
- PRIMARY SOURCE: Use the patient's actual report values as the definitive truth. If a patient asks about a level that is in their report, cite their exact observed number, unit, reference interval, and status (e.g. Normal, High, Low).
- SUPPORTING CONTEXT: Use the medical knowledge base to explain the physiological role of the biomarker, pre-analytical factors (hydration, fasting, exercise, diurnal variation), and potential questions for the doctor.
- ZERO DISEASE FABRICATION: You MUST NOT diagnose illnesses or declare diseases (e.g., do NOT state "You have kidney failure", "You have diabetes", "You have hepatitis", or "You have anemia"). Explain values as indicators that warrant clinical review.
- APPOINTMENT GUIDANCE: When asked about appointments or doctors, recommend the best-suited specialist from our available hospital physicians:
  * Dr. Sarah Jenkins (Cardiology) -> Lipid panels, cholesterol, cardiovascular metrics, blood pressure.
  * Dr. Rajiv Mehta (Endocrinology & Diabetology) -> Blood glucose, HbA1c, TSH, Free T4, metabolic hormones.
  * Dr. Elena Rostova (General Internal Medicine) -> Complete Blood Count (CBC), hemoglobin, general wellness, multi-system lab reviews.
  * Dr. Marcus Chen (Pulmonology & Respiratory Care) -> Respiratory markers, oxygenation, pulmonary health.
- Always be encouraging, warm, professional, and invite the patient to book an appointment with their linked report token.
"""

class RAGChatbotService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    def _find_matching_parameters(self, message: str, report_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans user query to find specific parameters mentioned from the patient's report.
        """
        if not report_data:
            return []

        analysis = report_data.get("analysis", {})
        params = analysis.get("parameters", [])
        lower_msg = message.lower()

        matched = []
        for p in params:
            name_lower = p.get("name", "").lower()
            # check main name or individual words (e.g., hemoglobin, creatinine, tsh, alt, ast, glucose)
            name_tokens = [t for t in re.split(r'[\s\(\)\/\-]+', name_lower) if len(t) >= 3]
            if name_lower in lower_msg or any(token in lower_msg for token in name_tokens):
                matched.append(p)

        # If user asks generally about "levels", "results", "report", or "abnormal/high/low"
        if not matched and any(w in lower_msg for w in ["level", "result", "report", "high", "low", "abnormal", "out of range", "flag"]):
            matched = [p for p in params if p.get("status") in ["High", "Low", "Borderline"]]
            if not matched:
                matched = params[:4]

        return matched

    def _determine_specialist_recommendation(
        self,
        message: str,
        matched_params: List[Dict[str, Any]],
        report_data: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Determines the most appropriate hospital doctor based on lab anomalies, user intent,
        report context, or multi-turn conversation history.
        """
        doctors = records_store.get_doctors()
        lower_msg = message.lower()

        # Check explicit doctor mentions
        for doc in doctors:
            if doc["name"].lower() in lower_msg or doc["specialty"].lower() in lower_msg:
                return doc

        # Check by directly matched parameters
        for p in matched_params:
            p_name = p.get("name", "").lower()
            if any(k in p_name for k in ["tsh", "t4", "t3", "thyroid", "glucose", "sugar", "hba1c"]):
                return next((d for d in doctors if d["id"] == "doc_2"), doctors[1]) # Dr. Rajiv Mehta (Endo)
            elif any(k in p_name for k in ["cholesterol", "lipid", "ldl", "hdl", "triglyceride"]):
                return next((d for d in doctors if d["id"] == "doc_1"), doctors[0]) # Dr. Sarah Jenkins (Cardio)
            elif any(k in p_name for k in ["lung", "respiratory", "oxygen", "spo2"]):
                return next((d for d in doctors if d["id"] == "doc_4"), doctors[3]) # Dr. Marcus Chen (Pulmonology)

        # Keyword checks in query
        if any(w in lower_msg for w in ["heart", "cardio", "chest", "bp", "cholesterol", "lipid"]):
            return next((d for d in doctors if d["id"] == "doc_1"), doctors[0])
        elif any(w in lower_msg for w in ["diabetes", "sugar", "thyroid", "tsh", "hormone", "endocrine", "metabolic"]):
            return next((d for d in doctors if d["id"] == "doc_2"), doctors[1])
        elif any(w in lower_msg for w in ["lung", "breath", "cough", "respiratory", "asthma", "pulmon"]):
            return next((d for d in doctors if d["id"] == "doc_4"), doctors[3])

        # Check multi-turn conversation history for context continuity
        if chat_history:
            history_text = " ".join([h.get("content", "").lower() for h in chat_history[-3:]])
            if any(w in history_text for w in ["thyroid", "tsh", "t4", "glucose", "diabetes", "endocrine"]):
                return next((d for d in doctors if d["id"] == "doc_2"), doctors[1])
            elif any(w in history_text for w in ["cholesterol", "lipid", "heart", "cardio", "blood pressure"]):
                return next((d for d in doctors if d["id"] == "doc_1"), doctors[0])
            elif any(w in history_text for w in ["lung", "respiratory", "cough", "asthma"]):
                return next((d for d in doctors if d["id"] == "doc_4"), doctors[3])

        # Check active report anomalies or title if loaded
        if report_data:
            analysis = report_data.get("analysis", {})
            title_lower = analysis.get("report_title", "").lower()
            if any(w in title_lower for w in ["thyroid", "endocrine", "metabolic", "glucose"]):
                return next((d for d in doctors if d["id"] == "doc_2"), doctors[1])
            elif any(w in title_lower for w in ["lipid", "cardio", "heart"]):
                return next((d for d in doctors if d["id"] == "doc_1"), doctors[0])
            elif any(w in title_lower for w in ["pulmonary", "respiratory"]):
                return next((d for d in doctors if d["id"] == "doc_4"), doctors[3])

            for p in analysis.get("parameters", []):
                if p.get("status") in ["High", "Low", "Borderline"]:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ["tsh", "t4", "glucose"]):
                        return next((d for d in doctors if d["id"] == "doc_2"), doctors[1])
                    elif any(k in p_name for k in ["cholesterol", "triglyceride", "lipid"]):
                        return next((d for d in doctors if d["id"] == "doc_1"), doctors[0])

        if any(w in lower_msg for w in ["doctor", "appointment", "consult", "visit", "schedule", "checkup"]):
            return next((d for d in doctors if d["id"] == "doc_3"), doctors[2]) # General physician default

        return None

    def _build_chat_context(
        self,
        user_message: str,
        report_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ):
        report_data = None
        if report_id:
            report_data = records_store.get_report(report_id) or records_store.get_report_by_token(report_id)

        matched_params = self._find_matching_parameters(user_message, report_data)

        rag_chunks = rag_engine.search_knowledge(user_message, top_k=3)
        for p in matched_params:
            extra = rag_engine.search_knowledge(p.get("name", ""), top_k=1)
            for ex in extra:
                if ex not in rag_chunks:
                    rag_chunks.append(ex)

        doctors = records_store.get_doctors()
        recommended_doc = self._determine_specialist_recommendation(
            message=user_message,
            matched_params=matched_params,
            report_data=report_data,
            chat_history=chat_history
        )

        return report_data, matched_params, rag_chunks, doctors, recommended_doc

    def chat(
        self,
        message: str,
        report_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous RAG chatbot execution for testing and offline execution.
        """
        report_data, matched_params, rag_chunks, doctors, recommended_doc = self._build_chat_context(message, report_id, history)
        
        reply_text = self._generate_grounded_fallback_response(
            user_message=message,
            report_data=report_data,
            matched_params=matched_params,
            recommended_doc=recommended_doc,
            rag_chunks=rag_chunks
        )

        return {
            "reply": reply_text,
            "response": reply_text,
            "doctor_recommendation": recommended_doc,
            "recommended_doctor": recommended_doc,
            "parameters_cited": [p.get("name") for p in matched_params],
            "matched_parameters": matched_params,
            "report_token": report_data.get("token") if report_data else None,
            "source": "MediSync Grounded RAG Chatbot Engine"
        }

    async def answer_chat(
        self,
        user_message: str,
        report_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generates a grounded RAG response incorporating patient report values,
        knowledge base explanations, and doctor appointment scheduling.
        """
        # 1. Build Context
        report_data, matched_params, rag_chunks, doctors, recommended_doc = self._build_chat_context(user_message, report_id, chat_history)

        # 2. Check if external Gemini API is available
        if self.api_key:
            try:
                report_context_str = "No specific patient laboratory report is currently loaded."
                if report_data:
                    analysis = report_data.get("analysis", {})
                    param_lines = [
                        f"- {p.get('name')}: Observed {p.get('value')} (Reference: {p.get('reference_range')}, Status: {p.get('status')})"
                        for p in analysis.get("parameters", [])
                    ]
                    report_context_str = (
                        f"PATIENT'S ACTIVE LABORATORY REPORT:\n"
                        f"Report Title: {analysis.get('report_title', 'Health Report')}\n"
                        f"Patient Name: {report_data.get('patient_name', 'Patient')}\n"
                        f"Report Token: {report_data.get('token', 'N/A')}\n"
                        f"Observed Parameters:\n" + "\n".join(param_lines)
                    )

                rag_kb_str = "\n".join([
                    f"KB Resource ({c.get('title')}): {c.get('content')}"
                    for c in rag_chunks[:4]
                ])

                doctors_str = "\n".join([
                    f"- {d['name']} ({d['specialty']}) at {d['hospital']} | Days: {', '.join(d.get('available_days', []))} ({d.get('available_time')})"
                    for d in doctors
                ])

                conversation_context = ""
                if chat_history:
                    formatted_history = []
                    for h in chat_history[-4:]:
                        role = "user" if h.get("role") == "user" else "model"
                        formatted_history.append(f"{role}: {h.get('content')}")
                    conversation_context = "PREVIOUS CONVERSATION:\n" + "\n".join(formatted_history) + "\n\n"

                full_prompt = (
                    f"{conversation_context}"
                    f"USER QUESTION: {user_message}\n\n"
                    f"{report_context_str}\n\n"
                    f"VERIFIED MEDICAL KNOWLEDGE BASE CONTEXT:\n{rag_kb_str}\n\n"
                    f"AVAILABLE HOSPITAL PHYSICIANS & SCHEDULES:\n{doctors_str}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"1. If answering about lab values, cite the exact numbers and ranges from the patient's report above.\n"
                    f"2. Use the knowledge base to explain the physiological role and variations (hydration, exercise, fasting).\n"
                    f"3. Strictly DO NOT diagnose diseases.\n"
                    f"4. If relevant, recommend the best-suited doctor ({recommended_doc['name'] if recommended_doc else 'our specialists'}) and explain how to book.\n"
                    f"5. Keep the response organized, empathetic, and clear with markdown bullet points."
                )

                payload = {
                    "system_instruction": {"parts": [{"text": RAG_CHATBOT_SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.25, "maxOutputTokens": 600}
                }

                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        f"{GEMINI_API_URL}?key={self.api_key}",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200:
                        cand = resp.json().get("candidates", [])
                        if cand:
                            answer = cand[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            return {
                                "reply": answer.strip(),
                                "response": answer.strip(),
                                "doctor_recommendation": recommended_doc,
                                "recommended_doctor": recommended_doc,
                                "parameters_cited": [p.get("name") for p in matched_params],
                                "matched_parameters": matched_params,
                                "report_token": report_data.get("token") if report_data else None,
                                "source": "Gemini-RAG Medical Chatbot"
                            }
            except Exception as e:
                print(f"Chatbot Gemini call error: {e}. Falling back to deterministic RAG engine.")

        # 3. Deterministic Grounded RAG Generator
        fallback_response = self._generate_grounded_fallback_response(
            user_message=user_message,
            report_data=report_data,
            matched_params=matched_params,
            recommended_doc=recommended_doc,
            rag_chunks=rag_chunks
        )

        return {
            "reply": fallback_response,
            "response": fallback_response,
            "doctor_recommendation": recommended_doc,
            "recommended_doctor": recommended_doc,
            "parameters_cited": [p.get("name") for p in matched_params],
            "matched_parameters": matched_params,
            "report_token": report_data.get("token") if report_data else None,
            "source": "MediSync Grounded RAG Chatbot Engine"
        }

    def _generate_grounded_fallback_response(
        self,
        user_message: str,
        report_data: Optional[Dict[str, Any]],
        matched_params: List[Dict[str, Any]],
        recommended_doc: Optional[Dict[str, Any]],
        rag_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Compiles accurate, clinically safe answers for levels and appointment booking without external LLM dependencies.
        """
        lower_msg = user_message.lower()
        parts = []

        is_asking_appointment = any(w in lower_msg for w in ["appointment", "book", "schedule", "doctor", "physician", "consult", "see someone", "who should i see"])
        is_asking_levels = bool(matched_params) or any(w in lower_msg for w in ["level", "test", "result", "high", "low", "abnormal", "range", "report", "value"])

        # 1. Answer regarding lab levels
        if is_asking_levels and report_data:
            analysis = report_data.get("analysis", {})
            parts.append(f"### 📊 Your Laboratory Levels Overview\n")
            
            if matched_params:
                for p in matched_params:
                    status_emoji = "🟢" if p.get("status") == "Normal" else ("🟡" if p.get("status") == "Borderline" else "🔴")
                    parts.append(
                        f"**{p.get('name')}**: **{p.get('value')}** ({status_emoji} {p.get('status')})\n"
                        f"- **Standard Reference Range**: `{p.get('reference_range')}`\n"
                        f"- **Clinical Context**: {p.get('explanation') or 'Key biomarker monitored for cellular and physiological health.'}\n"
                    )
                    if p.get("biological_limitations"):
                        parts.append(f"- *Pre-analytical note*: {p.get('biological_limitations')}\n")
            else:
                parts.append("All observed parameters in your current report have been recorded. You can ask me about any specific test (e.g. Hemoglobin, Glucose, Creatinine, TSH, ALT) for details.")

            parts.append("\n> **Educational Guardrail**: This clinical context is provided for educational purposes and does not provide a medical diagnosis or conclude illnesses. Laboratory reference boundaries represent population statistics; always discuss your findings with your doctor.")

        elif is_asking_levels and not report_data:
            parts.append("I don't have an uploaded laboratory report loaded for you yet. You can upload your PDF or image report in the **Upload & Analyze** tab, or load one of our clinical samples to explore your levels!")

        # 2. Answer regarding appointments & doctor recommendations
        if is_asking_appointment or recommended_doc:
            parts.append(f"\n### 📅 Doctor Consultation & Appointment Guidance\n")
            if recommended_doc:
                token_text = f" (Linked Report Token: `{report_data.get('token')}`)" if report_data else ""
                parts.append(
                    f"Based on your inquiry and laboratory profile, I recommend scheduling a consultation with:\n\n"
                    f"**{recommended_doc.get('avatar', '🩺')} {recommended_doc['name']}**\n"
                    f"- **Specialty**: {recommended_doc['specialty']} ({recommended_doc.get('qualification')})\n"
                    f"- **Center**: {recommended_doc['hospital']}\n"
                    f"- **Availability**: {', '.join(recommended_doc.get('available_days', []))} between {recommended_doc.get('available_time')}\n\n"
                    f"👉 You can book this appointment directly in the **Book Appointment** tab{token_text}. When you book, your doctor will have instant access to your AI-analyzed report for your visit."
                )
            else:
                parts.append(
                    "You can book a consultation with any of our hospital specialists in **Cardiology**, **Endocrinology**, **General Internal Medicine**, or **Pulmonology** using the **Book Appointment** tab above. Select your preferred date and time, and your report token will attach automatically."
                )

        if not parts:
            parts.append(
                f"Hello! I am your **MediSync RAG Assistant**. I can help you with two main areas:\n\n"
                f"1. **Your Lab Levels**: Ask me about any test in your report (e.g., *'Why is my hemoglobin 11.4?'*, *'Are my liver enzymes high?'*, *'What does my creatinine mean?'*).\n"
                f"2. **Appointment Scheduling**: Ask me *'Which doctor should I see?'*, *'How do I book an appointment?'*, or *'Can I schedule a consultation with Dr. Jenkins?'*."
            )

        return "\n".join(parts)

rag_chatbot = RAGChatbotService()
