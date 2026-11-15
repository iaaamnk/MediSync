import os
import json
import re
from typing import Dict, Any, List, Optional

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base", "medical_kb.json")

class ParameterParser:
    """
    Identifies lab parameters, extracts patient values and reference intervals,
    and performs objective threshold classification without making clinical diagnoses.
    """

    def __init__(self):
        self.kb = self._load_kb()

    def _load_kb(self) -> Dict[str, Any]:
        try:
            with open(KB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not load medical_kb.json: {e}")
            return {"panels": {}, "parameters": {}, "reference_range_limitations_guide": {}}

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extracts patient name, date, and specimen numbers from header text.
        """
        meta = {
            "patient_name": None,
            "sample_date": None,
            "lab_id": None
        }

        # Patient Name search
        name_match = re.search(r'(?:patient|name|patient\s*name)\s*[:\-\|]\s*([A-Za-z\s\.\,\'\-]+?)(?:\s{2,}|\n|\||age|sex|dob|\d)', text, re.IGNORECASE)
        if name_match:
            cand = name_match.group(1).strip()
            if len(cand) >= 2 and not any(w in cand.lower() for w in ["report", "lab", "date", "specimen"]):
                meta["patient_name"] = cand

        # Date search
        date_match = re.search(r'(?:date|collection\s*date|sample\s*date|reported)\s*[:\-\|]?\s*([0-9]{1,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,4})', text, re.IGNORECASE)
        if date_match:
            meta["sample_date"] = date_match.group(1).strip()

        # Lab ID / Ref ID
        ref_match = re.search(r'(?:lab\s*ref|sample\s*id|ref\s*no|bar\s*code|mrn)\s*[:\-\|]?\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
        if ref_match:
            meta["lab_id"] = ref_match.group(1).strip()

        return meta

    def parse_parameters(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans document text against medical knowledge base parameters,
        extracts observed values, units, and intervals, and computes mathematical status.
        """
        results = []
        kb_params = self.kb.get("parameters", {})
        lower_text = text.lower()

        for param_id, param_def in kb_params.items():
            canonical_name = param_def.get("canonical_name", param_id.title())
            aliases = [canonical_name.lower()] + [a.lower() for a in param_def.get("aliases", [])]
            unit = param_def.get("unit", "")
            default_interval = param_def.get("standard_reference_interval", "")

            # Sort aliases by length descending so longer phrases match first
            aliases.sort(key=len, reverse=True)

            found_match = False
            for alias in aliases:
                # Regex matching: alias followed by separators and a numeric value (e.g., "Hemoglobin : 11.4 g/dL")
                # Also capture optional trailing reference intervals (e.g. "(12.0 - 15.5)" or "Ref: 12.0 - 17.0")
                pattern = rf"(?:^|\b|\n){re.escape(alias)}[\s:\-=|\t]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z%\/µ\^0-9]+)?(?:[^\n\d]*?(\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?))?"
                
                for line in text.splitlines():
                    if alias in line.lower():
                        match = re.search(rf"(?:^|\b){re.escape(alias)}(?:\s*\(.*?\))?[\s:\-=|\t]+([<>]?\s*\d+(?:\.\d+)?)", line, re.IGNORECASE)
                        if match:
                            raw_val_str = match.group(1).strip()
                            clean_num_str = re.sub(r'[^\d\.]', '', raw_val_str)
                            
                            try:
                                num_val = float(clean_num_str)
                            except ValueError:
                                continue

                            # Detect unit from line or fallback to KB unit
                            detected_unit = unit
                            unit_match = re.search(rf"{re.escape(raw_val_str)}\s*([a-zA-Z%\/µ\^0-9]+)", line)
                            if unit_match and len(unit_match.group(1)) <= 10:
                                detected_unit = unit_match.group(1).strip()

                            # Detect reference interval printed on the same line if available
                            detected_interval = default_interval
                            range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)', line)
                            min_ref = None
                            max_ref = None
                            
                            if range_match:
                                try:
                                    min_ref = float(range_match.group(1))
                                    max_ref = float(range_match.group(2))
                                    detected_interval = f"{min_ref} - {max_ref} {detected_unit}"
                                except ValueError:
                                    pass

                            # If no range found on line, parse from standard KB interval
                            if min_ref is None or max_ref is None:
                                kb_range_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', default_interval)
                                if kb_range_match:
                                    try:
                                        min_ref = float(kb_range_match.group(1))
                                        max_ref = float(kb_range_match.group(2))
                                    except ValueError:
                                        pass

                            # Classify status mathematically
                            status = "Normal"
                            is_out_of_range = False
                            if min_ref is not None and max_ref is not None:
                                if num_val < min_ref:
                                    status = "Low"
                                    is_out_of_range = True
                                elif num_val > max_ref:
                                    status = "High"
                                    is_out_of_range = True
                            elif "≥" in default_interval or ">=" in default_interval:
                                bound_match = re.search(r'\d+(?:\.\d+)?', default_interval)
                                if bound_match and num_val < float(bound_match.group(0)):
                                    status = "Low"
                                    is_out_of_range = True
                            elif "<" in default_interval:
                                bound_match = re.search(r'\d+(?:\.\d+)?', default_interval)
                                if bound_match and num_val > float(bound_match.group(0)):
                                    status = "High"
                                    is_out_of_range = True

                            results.append({
                                "id": param_id,
                                "name": canonical_name,
                                "panel": param_def.get("panel", "general"),
                                "value": f"{raw_val_str} {detected_unit}".strip(),
                                "numeric_value": num_val,
                                "unit": detected_unit,
                                "reference_range": detected_interval,
                                "status": status,
                                "is_out_of_range": is_out_of_range,
                                "clinical_definition": param_def.get("clinical_definition", ""),
                                "elevation_interpretation": param_def.get("elevation_interpretation", ""),
                                "decrease_interpretation": param_def.get("decrease_interpretation", ""),
                                "biological_limitations": param_def.get("biological_limitations", ""),
                                "doctor_discussion_points": param_def.get("doctor_discussion_points", "")
                            })
                            found_match = True
                            break
                if found_match:
                    break

        return results

parameter_parser = ParameterParser()
