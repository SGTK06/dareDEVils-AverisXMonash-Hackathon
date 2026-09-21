import os
import json
import glob
from pathlib import Path
import math
import re

import spacy
import compare

# --- CLASSIFIER LOGIC ---

DEFAULT_CATEGORIES = {
    "BL_COMPARISON": "Comparison requested for the Bill of Landing (BL) and Shipping Instruction (SI)",
    "SI_REQUEST": "Request for new Shipping Information (SI)",
    "INVOICE_QUERY": "Query about an invoice, billing, or charges",
    "GENERAL": "General business message or operational update",
    "SPAM": "Unwanted marketing, phishing, or fraudulent message",
}

LEXICAL_RULES = {
    "BL_COMPARISON": {
        "compare bl and si": 4.0, "compare the bl and si": 4.0, "compare si and bl": 4.0,
        "bl against the si": 4.0, "si against the bl": 4.0, "draft bl against the si": 4.0,
        "bl and si": 3.0,
    },
    "SI_REQUEST": {
        "request si": 3.0, "shipping instruction for": 3.0, "si needed": 3.0,
        "cust si": 3.0, "latest si": 2.0, "please find shipping instruction": 3.0,
    },
    "INVOICE_QUERY": {
        "invoice": 2.0, "billing": 2.0, "local charge": 2.5, "d & d": 2.5,
        "detention charge": 2.5, "missing gr": 3.0, "cancel invoice": 3.0, "payment": 1.5,
    },
    "GENERAL": {
        "update summary": 3.0, "berthing report": 3.0, "outstanding bl": 3.0, "rpa": 2.5,
        "automated notification": 2.5, "reminder": 1.5, "time off request": 2.0,
        "happy and prosperous": 2.0,
    },
    "SPAM": {
        "claim now": 3.0, "to claim": 2.5, "you have won": 3.0, "prize": 2.5,
        "short survey": 2.5, "gift card": 3.0, "click here": 2.5, "limited time offer": 3.0,
        "90% off": 3.0, "buy now": 2.5, "weird trick": 2.5, "hot singles": 3.0,
        "bitcoin": 3.0, "customs fee": 3.0, "parcel will be returned": 3.0,
        "bank details": 3.0, "business proposal": 2.5, "urgent business": 2.5,
        "verify your account": 2.5, "storage limit": 2.5, "exclusive offer": 2.5,
        "undelivered messages": 2.5,
    },
}


def email_text(email):
    attachments = email.get("attachments", []) or []
    if not isinstance(attachments, list):
        attachments = [attachments]
    fields = [
        email.get("from", ""), email.get("subject", ""), email.get("body", ""),
        " ".join(str(a) for a in attachments),
    ]
    return " ".join(str(field) for field in fields if field)


def lexical_scores(text):
    text = text.lower()
    return {
        label: sum(weight for phrase, weight in rules.items() if phrase in text)
        for label, rules in LEXICAL_RULES.items()
    }


def has_bl_si_comparison(text):
    text = text.lower()
    mentions_bl = bool(re.search(r"\bbl\b", text)) or "bill of lading" in text
    mentions_si = bool(re.search(r"\bsi\b", text)) or "shipping instruction" in text
    return mentions_bl and mentions_si


def is_standalone_bl_request(text):
    text = text.lower()
    mentions_bl = bool(re.search(r"\bbl\b", text)) or "bill of lading" in text
    mentions_si = bool(re.search(r"\bsi\b", text)) or "shipping instruction" in text
    request_phrases = ("draft bl", "amend bl", "confirm bl", "send draft bl", "check draft bl")
    return mentions_bl and not mentions_si and any(phrase in text for phrase in request_phrases)


class SimilarityClassifier:
    def __init__(self, model_name="en_core_web_md", categories=None, temperature=0.15):
        try:
            self.nlp = spacy.load(model_name)
        except OSError as exc:
            raise OSError(f"Install the spaCy vector model first: python -m spacy download {model_name}") from exc
        
        self.categories = categories or DEFAULT_CATEGORIES
        self.category_docs = {label: self.nlp(desc) for label, desc in self.categories.items()}
        self.temperature = temperature

    def classify(self, email):
        text = email_text(email)
        document = self.nlp(text)
        similarities = {label: document.similarity(doc) for label, doc in self.category_docs.items()}
        keyword_scores = lexical_scores(text)
        
        if not has_bl_si_comparison(text):
            keyword_scores["BL_COMPARISON"] = 0.0
            
        combined_scores = {label: similarities[label] + keyword_scores[label] for label in self.categories}
        
        if not has_bl_si_comparison(text):
            combined_scores["BL_COMPARISON"] = -1e6
        if is_standalone_bl_request(text):
            combined_scores["GENERAL"] = max(combined_scores.values()) + 1.0

        highest_similarity = max(combined_scores.values())
        exponentials = {label: math.exp((score - highest_similarity) / self.temperature) for label, score in combined_scores.items()}
        total = sum(exponentials.values())
        confidence_scores = {label: value / total for label, value in exponentials.items()}
        label = max(confidence_scores, key=confidence_scores.get)

        return {"label": label, "confidence": confidence_scores[label]}


# --- PIPELINE LOGIC ---

def run_pipeline():
    print("Loading spaCy model...")
    try:
        classifier = SimilarityClassifier()
    except OSError:
        import subprocess
        print("Downloading en_core_web_md model...")
        subprocess.check_call(["python", "-m", "spacy", "download", "en_core_web_md"])
        classifier = SimilarityClassifier()

    inbox_dir = "data_v2/inbox"
    email_files = sorted(glob.glob(os.path.join(inbox_dir, "email_*.json")))
    
    submission = {}
    
    print(f"Processing {len(email_files)} emails...")
    for idx, filepath in enumerate(email_files, 1):
        with open(filepath, 'r', encoding='utf-8') as f:
            email = json.load(f)
            
        email_id = email["email_id"]
        
        # 1. Stage 1: Classification
        cat_result = classifier.classify(email)
        cat = cat_result["label"]
        
        sub_entry = {
            "category": cat,
            "status": "OK",
            "review_reason": None,
            "defect_fields": [],
            "has_defect": False
        }
        
        # 2. Stage 3: BL Comparison (Only if classified as BL_COMPARISON)
        if cat == "BL_COMPARISON":
            try:
                # Find attachments and process them
                results = compare.compare_email_dataset(email_id, "data_v2")
                verdicts = {f: res['verdict'] for f, res in results.items()}
                
                if "MISMATCH" in verdicts.values():
                    sub_entry["status"] = "REJECTED"
                    sub_entry["has_defect"] = True
                    sub_entry["defect_fields"] = [f for f, v in verdicts.items() if v == "MISMATCH"]
                elif "REVIEW" in verdicts.values():
                    sub_entry["status"] = "NEEDS_REVIEW"
                    sub_entry["review_reason"] = "Document fields need manual review"
                else:
                    sub_entry["status"] = "OK"
                    
            except Exception as e:
                # If attachment parsing fails or something goes wrong, escalate
                sub_entry["status"] = "NEEDS_REVIEW"
                sub_entry["review_reason"] = str(e)
                
        submission[email_id] = sub_entry
        if idx % 50 == 0:
            print(f"Processed {idx}/{len(email_files)}...")

    with open("submission.json", "w") as f:
        json.dump(submission, f, indent=2)
        
    print("Pipeline complete. Generated submission.json.")
    print("To test accuracy, run: python server/score_cli.py submission.json")

if __name__ == "__main__":
    run_pipeline()
