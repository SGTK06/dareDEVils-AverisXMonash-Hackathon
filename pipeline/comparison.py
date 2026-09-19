"""Email classification using spaCy document similarity."""

import math
import re

import spacy


DEFAULT_CATEGORIES = {
	"BL_COMPARISON": (
		"Comparison requested for the Bill of Landing (BL) and "
		"Shipping Instruction (SI)"
	),
	"SI_REQUEST": "Request for new Shipping Information (SI)",
	"INVOICE_QUERY": "Query about an invoice, billing, or charges",
	"GENERAL": "General business message or operational update",
	"SPAM": "Unwanted marketing, phishing, or fraudulent message",
}

LEXICAL_RULES = {
	"BL_COMPARISON": {
		"compare bl and si": 4.0,
		"compare the bl and si": 4.0,
		"compare si and bl": 4.0,
		"bl against the si": 4.0,
		"si against the bl": 4.0,
		"draft bl against the si": 4.0,
		"bl and si": 3.0,
	},
	"SI_REQUEST": {
		"request si": 3.0,
		"shipping instruction for": 3.0,
		"si needed": 3.0,
		"cust si": 3.0,
		"latest si": 2.0,
		"please find shipping instruction": 3.0,
	},
	"INVOICE_QUERY": {
		"invoice": 2.0,
		"billing": 2.0,
		"local charge": 2.5,
		"d & d": 2.5,
		"detention charge": 2.5,
		"missing gr": 3.0,
		"cancel invoice": 3.0,
		"payment": 1.5,
	},
	"GENERAL": {
		"update summary": 3.0,
		"berthing report": 3.0,
		"outstanding bl": 3.0,
		"rpa": 2.5,
		"automated notification": 2.5,
		"reminder": 1.5,
		"time off request": 2.0,
		"happy and prosperous": 2.0,
	},
	"SPAM": {
		"claim now": 3.0,
		"to claim": 2.5,
		"you have won": 3.0,
		"prize": 2.5,
		"short survey": 2.5,
		"gift card": 3.0,
		"click here": 2.5,
		"limited time offer": 3.0,
		"90% off": 3.0,
		"buy now": 2.5,
		"weird trick": 2.5,
		"hot singles": 3.0,
		"bitcoin": 3.0,
		"customs fee": 3.0,
		"parcel will be returned": 3.0,
		"bank details": 3.0,
		"business proposal": 2.5,
		"urgent business": 2.5,
		"verify your account": 2.5,
		"storage limit": 2.5,
		"exclusive offer": 2.5,
		"undelivered messages": 2.5,
	},
}


def email_text(email):
	"""Build the text representation used for similarity matching."""
	attachments = email.get("attachments", []) or []
	if not isinstance(attachments, list):
		attachments = [attachments]

	fields = [
		email.get("from", ""),
		email.get("subject", ""),
		email.get("body", ""),
		" ".join(str(attachment) for attachment in attachments),
	]
	return " ".join(str(field) for field in fields if field)


def lexical_scores(text):
	"""Score distinctive phrases that generic embeddings can confuse."""
	text = text.lower()
	return {
		label: sum(weight for phrase, weight in rules.items() if phrase in text)
		for label, rules in LEXICAL_RULES.items()
	}


def has_bl_si_comparison(text):
	"""Return whether the email explicitly compares BL and SI documents."""
	text = text.lower()
	comparison_words = ("compare", "comparison", "check", "confirm", "verify")
	mentions_bl = bool(re.search(r"\bbl\b", text)) or "bill of lading" in text
	mentions_si = bool(re.search(r"\bsi\b", text)) or "shipping instruction" in text
	return (
		mentions_bl
		and mentions_si
		and any(word in text for word in comparison_words)
	)


def is_standalone_bl_request(text):
	"""Identify BL requests that do not mention an SI comparison."""
	text = text.lower()
	mentions_bl = bool(re.search(r"\bbl\b", text)) or "bill of lading" in text
	mentions_si = bool(re.search(r"\bsi\b", text)) or "shipping instruction" in text
	request_phrases = (
		"draft bl",
		"amend bl",
		"confirm bl",
		"send draft bl",
		"check draft bl",
	)
	return mentions_bl and not mentions_si and any(
		phrase in text for phrase in request_phrases
	)


class SimilarityClassifier:
	"""Classify emails against category descriptions with spaCy vectors.

	``confidence`` is a softmax-normalized score relative to the configured
	categories. It is useful for escalation, but is not a calibrated
	probability until it has been evaluated on labelled validation data.
	"""

	def __init__(
		self,
		model_name="en_core_web_md",
		categories=None,
		temperature=0.15,
	):
		if temperature <= 0:
			raise ValueError("temperature must be greater than zero")

		try:
			self.nlp = spacy.load(model_name)
		except OSError as exc:
			raise OSError(
				f"Install the spaCy vector model first: "
				f"python -m spacy download {model_name}"
			) from exc

		self.categories = categories or DEFAULT_CATEGORIES
		self.category_docs = {
			label: self.nlp(description)
			for label, description in self.categories.items()
		}
		self.temperature = temperature

	def classify(self, email):
		"""Return the predicted label, confidence, and category scores."""
		text = email_text(email)
		document = self.nlp(text)
		similarities = {
			label: document.similarity(category_doc)
			for label, category_doc in self.category_docs.items()
		}
		keyword_scores = lexical_scores(text)
		if not has_bl_si_comparison(text):
			keyword_scores["BL_COMPARISON"] = 0.0
		combined_scores = {
			label: similarities[label] + keyword_scores[label]
			for label in self.categories
		}
		if not has_bl_si_comparison(text):
			combined_scores["BL_COMPARISON"] = -1e6
		if is_standalone_bl_request(text):
			combined_scores["GENERAL"] = max(combined_scores.values()) + 1.0

		highest_similarity = max(combined_scores.values())
		exponentials = {
			label: math.exp(
				(score - highest_similarity) / self.temperature
			)
			for label, score in combined_scores.items()
		}
		total = sum(exponentials.values())
		confidence_scores = {
			label: value / total for label, value in exponentials.items()
		}
		label = max(confidence_scores, key=confidence_scores.get)

		return {
			"label": label,
			"confidence": confidence_scores[label],
			"similarity": similarities[label],
			"keyword_scores": keyword_scores,
			"scores": confidence_scores,
		}

	def classify_many(self, emails):
		"""Classify an iterable of email dictionaries."""
		return [self.classify(email) for email in emails]
