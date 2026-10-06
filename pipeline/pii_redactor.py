import re
import os
import pandas as pd
from typing import Tuple, List, Dict, Any
from datetime import datetime

# Ultra-fast regex patterns for standard PII
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b')
URL_REGEX = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+|www\.[-\w.]+')
# Common user name patterns in review feedback (e.g., "by John Doe", "user Jane Smith", "developer Sarah")
NAME_INDICATOR_REGEX = re.compile(r'\b(user|developer|contact|reach|mr\.|mrs\.|ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', re.IGNORECASE)

class PIIShield:
    """
    Enterprise PII Redaction Engine.
    Masks emails, phone numbers, URLs, and identified customer names.
    Produces compliance before/after audit logs.
    """
    def __init__(self, use_spacy: bool = False):
        self.use_spacy = use_spacy
        self.nlp = None
        if use_spacy:
            try:
                import spacy
                self.nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
            except Exception as e:
                print(f"Warning: spaCy NER not loaded ({e}), falling back to regex.")
                self.use_spacy = False

    def redact_text(self, text: str, review_id: str = "") -> Tuple[str, List[Dict[str, Any]]]:
        audit_events = []
        redacted = text

        # 1. Emails
        for match in EMAIL_REGEX.finditer(text):
            original = match.group(0)
            redacted = redacted.replace(original, "[REDACTED_EMAIL]")
            audit_events.append({
                "review_id": review_id,
                "pii_type": "EMAIL",
                "original": original,
                "redacted": "[REDACTED_EMAIL]",
                "timestamp": datetime.now().isoformat()
            })

        # 2. Phones
        for match in PHONE_REGEX.finditer(text):
            original = match.group(0)
            # Avoid redacting simple version strings like 3.4.0
            if "." in original and len(original.split(".")) > 2:
                continue
            if len(re.sub(r'\D', '', original)) >= 7:
                redacted = redacted.replace(original, "[REDACTED_PHONE]")
                audit_events.append({
                    "review_id": review_id,
                    "pii_type": "PHONE",
                    "original": original,
                    "redacted": "[REDACTED_PHONE]",
                    "timestamp": datetime.now().isoformat()
                })

        # 3. URLs
        for match in URL_REGEX.finditer(text):
            original = match.group(0)
            redacted = redacted.replace(original, "[REDACTED_URL]")
            audit_events.append({
                "review_id": review_id,
                "pii_type": "URL",
                "original": original,
                "redacted": "[REDACTED_URL]",
                "timestamp": datetime.now().isoformat()
            })

        # 4. Name Indicators
        for match in NAME_INDICATOR_REGEX.finditer(text):
            full_match = match.group(0)
            name_part = match.group(2)
            if name_part.lower() not in ["telegram", "android", "ios", "google", "app", "phone"]:
                redacted = redacted.replace(name_part, "[REDACTED_NAME]")
                audit_events.append({
                    "review_id": review_id,
                    "pii_type": "PERSON_NAME",
                    "original": name_part,
                    "redacted": "[REDACTED_NAME]",
                    "timestamp": datetime.now().isoformat()
                })

        return redacted, audit_events

    def redact_dataframe(self, df: pd.DataFrame, text_col: str = "review_text", id_col: str = "review_id") -> Tuple[pd.DataFrame, pd.DataFrame]:
        df = df.copy()
        all_audit_logs = []
        redacted_texts = []

        for _, row in df.iterrows():
            rev_id = str(row[id_col])
            raw_text = str(row[text_col])
            redacted, audits = self.redact_text(raw_text, review_id=rev_id)
            redacted_texts.append(redacted)
            all_audit_logs.extend(audits)

        df["raw_review_text"] = df[text_col]
        df[text_col] = redacted_texts
        df_audit = pd.DataFrame(all_audit_logs)
        
        return df, df_audit

if __name__ == "__main__":
    shield = PIIShield()
    sample = "Please contact user Sarah Jenkins at sarah.j@company.com or call 415-555-2671."
    redacted, events = shield.redact_text(sample, "REV-001")
    print("Original:", sample)
    print("Redacted:", redacted)
    print("Audits detected:", len(events))
