"""PII redaction with regex and Named Entity Recognition."""

import re
from typing import Any, Optional

try:
    import spacy
    from spacy import displacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class Redactor:
    """Redactor for PII and sensitive information."""

    def __init__(
        self,
        allowlist: Optional[list[str]] = None,
        denylist: Optional[list[str]] = None,
        use_ner: bool = True,
    ):
        """Initialize redactor.

        Args:
            allowlist: List of patterns/terms to never redact
            denylist: List of patterns/terms to always redact
            use_ner: Whether to use Named Entity Recognition (requires spacy)
        """
        self.allowlist = allowlist or []
        self.denylist = denylist or []
        self.use_ner = use_ner and SPACY_AVAILABLE

        # Load spaCy model if available
        self.nlp = None
        if self.use_ner:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Model not installed, disable NER
                self.use_ner = False

        # Common PII patterns (regex)
        self.patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            "url": r"https?://[^\s]+",
        }

    def _is_allowed(self, text: str) -> bool:
        """Check if text is in allowlist.

        Args:
            text: Text to check

        Returns:
            True if text should not be redacted
        """
        text_lower = text.lower()
        for allowed in self.allowlist:
            if allowed.lower() in text_lower or text_lower in allowed.lower():
                return True
        return False

    def _is_denied(self, text: str) -> bool:
        """Check if text is in denylist.

        Args:
            text: Text to check

        Returns:
            True if text should be redacted
        """
        text_lower = text.lower()
        for denied in self.denylist:
            if denied.lower() in text_lower or text_lower in denied.lower():
                return True
        return False

    def _redact_with_regex(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Redact PII using regex patterns.

        Args:
            text: Text to redact

        Returns:
            Tuple of (redacted_text, list of redactions)
        """
        redacted = text
        redactions = []

        for pattern_name, pattern in self.patterns.items():
            matches = list(re.finditer(pattern, redacted, re.IGNORECASE))
            for match in reversed(matches):  # Reverse to maintain positions
                matched_text = match.group(0)
                
                # Check allowlist
                if self._is_allowed(matched_text):
                    continue
                
                # Check denylist
                if self._is_denied(matched_text):
                    replacement = f"[REDACTED_{pattern_name.upper()}]"
                    redacted = redacted[: match.start()] + replacement + redacted[match.end() :]
                    redactions.append(
                        {
                            "type": pattern_name,
                            "original": matched_text,
                            "position": (match.start(), match.end()),
                        }
                    )

        return redacted, redactions

    def _redact_with_ner(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Redact PII using Named Entity Recognition.

        Args:
            text: Text to redact

        Returns:
            Tuple of (redacted_text, list of redactions)
        """
        if not self.nlp:
            return text, []

        doc = self.nlp(text)
        redacted = text
        redactions = []

        # Entities to redact: PERSON, ORG, GPE (locations), MONEY, DATE (if sensitive)
        sensitive_entities = ["PERSON", "ORG", "GPE", "MONEY"]

        # Process entities in reverse order to maintain positions
        entities = sorted(doc.ents, key=lambda e: e.start_char, reverse=True)

        for ent in entities:
            if ent.label_ in sensitive_entities:
                entity_text = ent.text
                
                # Check allowlist
                if self._is_allowed(entity_text):
                    continue
                
                # Check denylist
                if self._is_denied(entity_text):
                    replacement = f"[REDACTED_{ent.label_}]"
                    redacted = redacted[: ent.start_char] + replacement + redacted[ent.end_char :]
                    redactions.append(
                        {
                            "type": f"NER_{ent.label_}",
                            "original": entity_text,
                            "position": (ent.start_char, ent.end_char),
                        }
                    )

        return redacted, redactions

    def redact(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Redact PII and sensitive information from text.

        Args:
            text: Text to redact

        Returns:
            Tuple of (redacted_text, list of redactions made)
        """
        if not text:
            return text, []

        # Apply regex patterns first
        redacted, regex_redactions = self._redact_with_regex(text)

        # Apply NER if enabled
        if self.use_ner:
            redacted, ner_redactions = self._redact_with_ner(redacted)
            all_redactions = regex_redactions + ner_redactions
        else:
            all_redactions = regex_redactions

        return redacted, all_redactions

    def check_for_pii(self, text: str) -> bool:
        """Check if text contains potential PII without redacting.

        Args:
            text: Text to check

        Returns:
            True if PII is detected
        """
        if not text:
            return False

        # Check regex patterns
        for pattern in self.patterns.values():
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check NER if enabled
        if self.use_ner and self.nlp:
            doc = self.nlp(text)
            sensitive_entities = ["PERSON", "ORG", "GPE", "MONEY"]
            for ent in doc.ents:
                if ent.label_ in sensitive_entities and not self._is_allowed(ent.text):
                    return True

        return False


def get_redactor(config: Optional[dict[str, Any]] = None) -> Redactor:
    """Get a configured Redactor instance.

    Args:
        config: Configuration dictionary with allowlist, denylist, use_ner

    Returns:
        Configured Redactor instance
    """
    if config is None:
        from mtm.config import get_config

        config_obj = get_config()
        # Try to load redaction config from config file
        config = {}

    allowlist = config.get("allowlist", [])
    denylist = config.get("denylist", [])
    use_ner = config.get("use_ner", True)

    return Redactor(allowlist=allowlist, denylist=denylist, use_ner=use_ner)

