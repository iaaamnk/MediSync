import os
import json
import re
from typing import Dict, Any, List, Optional

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base", "medical_kb.json")

class MedicalRAGEngine:
    """
    Retrieval-Augmented Generation (RAG) engine for medical laboratory interpretation.
    Provides verified clinical knowledge chunks, test descriptions, reference limitations,
    and discussion points to ground model generation.
    """

    def __init__(self):
        self.kb = self._load_kb()
        self.indexed_chunks = self._build_knowledge_index()

    def _load_kb(self) -> Dict[str, Any]:
        try:
            with open(KB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading medical_kb.json in RAG engine: {e}")
            return {"panels": {}, "parameters": {}, "reference_range_limitations_guide": {}}

    def _build_knowledge_index(self) -> List[Dict[str, Any]]:
        """
        Decomposes the medical knowledge base into searchable, modular knowledge documents.
        """
        chunks = []

        # 1. Index Panels
        for panel_id, panel_data in self.kb.get("panels", {}).items():
            chunks.append({
                "chunk_id": f"panel_{panel_id}",
                "type": "panel_overview",
                "panel_id": panel_id,
                "title": panel_data.get("name", ""),
                "content": f"{panel_data.get('name')}: {panel_data.get('clinical_overview')} Purpose: {panel_data.get('clinical_purpose')}",
                "source": panel_data.get("reference_source", "Clinical Laboratory Practice"),
                "keywords": [panel_id, panel_data.get("name", "").lower(), "panel", "test", "overview"]
            })

        # 2. Index Parameters
        for param_id, param_data in self.kb.get("parameters", {}).items():
            name = param_data.get("canonical_name", param_id)
            panel = param_data.get("panel", "general")
            content = (
                f"{name} ({param_data.get('unit')}): {param_data.get('clinical_definition')} "
                f"Reference range: {param_data.get('standard_reference_interval')}. "
                f"Elevations context: {param_data.get('elevation_interpretation')} "
                f"Decreased context: {param_data.get('decrease_interpretation')} "
                f"Biological and pre-analytical limitations: {param_data.get('biological_limitations')}"
            )
            keywords = [param_id, name.lower()] + [a.lower() for a in param_data.get("aliases", [])] + [panel]

            chunks.append({
                "chunk_id": f"param_{param_id}",
                "type": "parameter_guide",
                "param_id": param_id,
                "title": name,
                "panel": panel,
                "content": content,
                "doctor_questions": param_data.get("doctor_discussion_points", ""),
                "source": "ADLM Clinical Reference / Tietz Clinical Chemistry",
                "keywords": keywords
            })

        # 3. Index Reference Range Limitations Guide
        guide = self.kb.get("reference_range_limitations_guide", {})
        for idx, principle in enumerate(guide.get("core_principles", [])):
            chunks.append({
                "chunk_id": f"principle_{idx}",
                "type": "reference_limitation",
                "title": principle.get("principle", ""),
                "content": f"{principle.get('principle')}: {principle.get('explanation')}",
                "source": "Clinical Laboratory Standards & Evidence-Based Medicine",
                "keywords": ["reference range", "limitations", "confidence interval", "pre-analytical", "assay", "false positive", "cutoff"]
            })

        return chunks

    def retrieve_context_for_parameters(self, detected_parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Retrieves matching clinical knowledge chunks for all parameters detected in a patient's report.
        """
        matched_chunks = []
        referenced_panels = set()
        citations = []

        # Find exact parameter chunks
        for param in detected_parameters:
            param_id = param.get("id")
            panel_id = param.get("panel")
            if panel_id:
                referenced_panels.add(panel_id)

            for chunk in self.indexed_chunks:
                if chunk.get("type") == "parameter_guide" and chunk.get("param_id") == param_id:
                    matched_chunks.append({
                        "parameter": param.get("name"),
                        "observed_patient_value": param.get("value"),
                        "status": param.get("status"),
                        "clinical_definition": chunk.get("title"),
                        "educational_content": chunk.get("content"),
                        "biological_limitations": chunk.get("content").split("Biological and pre-analytical limitations:")[-1].strip(),
                        "doctor_questions": chunk.get("doctor_questions"),
                        "source": chunk.get("source")
                    })
                    if chunk.get("source") not in citations:
                        citations.append(chunk.get("source"))

        # Retrieve relevant panel overviews
        panel_overviews = []
        for panel_id in referenced_panels:
            for chunk in self.indexed_chunks:
                if chunk.get("type") == "panel_overview" and chunk.get("panel_id") == panel_id:
                    panel_overviews.append({
                        "panel_name": chunk.get("title"),
                        "description": chunk.get("content"),
                        "source": chunk.get("source")
                    })
                    if chunk.get("source") not in citations:
                        citations.append(chunk.get("source"))

        # Always attach reference range limitations context
        limitations = [
            c.get("content") for c in self.indexed_chunks if c.get("type") == "reference_limitation"
        ]

        # Authoritative reference materials
        authoritative_sources = self.kb.get("reference_range_limitations_guide", {}).get("authoritative_references", [])

        return {
            "parameter_contexts": matched_chunks,
            "panel_overviews": panel_overviews,
            "range_limitations": limitations,
            "citations": citations,
            "authoritative_sources": authoritative_sources
        }

    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Lexical search across the knowledge base (e.g. for voice pipeline questions).
        """
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []

        for chunk in self.indexed_chunks:
            score = 0
            chunk_text = (chunk.get("title", "") + " " + chunk.get("content", "") + " " + " ".join(chunk.get("keywords", []))).lower()
            
            for word in query_words:
                if len(word) >= 3:
                    if word in chunk.get("keywords", []):
                        score += 5
                    elif word in chunk_text:
                        score += 2

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

rag_engine = MedicalRAGEngine()

