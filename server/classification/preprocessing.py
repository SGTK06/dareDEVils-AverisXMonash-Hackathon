"""Shared email text preprocessing used by training and inference."""
import re
from pathlib import Path

def preprocess_email(email: dict) -> str:
    subject = str(email.get("subject", ""))
    body = str(email.get("body", ""))
    attachments = " ".join(Path(str(value)).name.replace("_", " ") for value in (email.get("attachments", []) or []))
    body = re.split(r"\n\s*(?:From:|-----Original Message-----|Best Regards|Kind regards)", body, flags=re.I)[0]
    body = re.sub(r"WARNING: This email originated outside.*?(?=\n|$)", " ", body, flags=re.I | re.S)
    text = f"subject: {subject} body: {body} attachments: {attachments}"
    text = re.sub(r"https?://\S+|\S+@\S+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9_\s]", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()
