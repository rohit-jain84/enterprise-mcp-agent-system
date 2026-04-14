"""
PII detection and redaction using Microsoft Presidio.

Wraps presidio-analyzer and presidio-anonymizer to scan text for personally
identifiable information (emails, phone numbers, SSNs, names, etc.), redact
matches with human-readable placeholders, and log detections for the audit
trail.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Presidio is an optional dependency; the module degrades gracefully.
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning(
        "presidio-analyzer / presidio-anonymizer not installed. "
        "PII detection will be unavailable."
    )

# Human-readable placeholders keyed by Presidio entity type.
_PLACEHOLDER_MAP: dict[str, str] = {
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[PHONE]",
    "US_SSN": "[SSN]",
    "PERSON": "[NAME]",
    "CREDIT_CARD": "[CREDIT_CARD]",
    "US_DRIVER_LICENSE": "[DRIVER_LICENSE]",
    "US_PASSPORT": "[PASSPORT]",
    "IP_ADDRESS": "[IP_ADDRESS]",
    "US_BANK_NUMBER": "[BANK_ACCOUNT]",
    "IBAN_CODE": "[IBAN]",
    "NRP": "[NATIONALITY]",
    "LOCATION": "[LOCATION]",
    "DATE_TIME": "[DATE]",
    "US_ITIN": "[ITIN]",
    "MEDICAL_LICENSE": "[MEDICAL_LICENSE]",
    "URL": "[URL]",
}

# Default entity types to scan for.
_DEFAULT_ENTITIES: list[str] = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "PERSON",
    "CREDIT_CARD",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "IP_ADDRESS",
    "US_BANK_NUMBER",
    "IBAN_CODE",
]


class PIIDetector:
    """Detect and redact PII using Microsoft Presidio.

    Parameters
    ----------
    entities : list[str] | None
        Presidio entity types to detect. Defaults to a broad set covering
        emails, phone numbers, SSNs, names, credit cards, and more.
    language : str
        Language code for the analyzer (default ``"en"``).
    score_threshold : float
        Minimum confidence score (0.0 - 1.0) for a detection to be
        considered valid. Default ``0.5``.
    """

    def __init__(
        self,
        entities: Optional[list[str]] = None,
        language: str = "en",
        score_threshold: float = 0.5,
    ) -> None:
        self._entities = entities or _DEFAULT_ENTITIES
        self._language = language
        self._score_threshold = score_threshold

        self._analyzer: Optional[Any] = None
        self._anonymizer: Optional[Any] = None
        self._available: bool = False

        self._initialize_engines()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_engines(self) -> None:
        """Create Presidio analyzer and anonymizer engines."""
        if not PRESIDIO_AVAILABLE:
            logger.info("Presidio unavailable; PII detection disabled.")
            return

        try:
            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            self._available = True
            logger.info(
                "PIIDetector initialised (entities=%s, threshold=%.2f).",
                self._entities,
                self._score_threshold,
            )
        except Exception:
            logger.exception("Failed to initialise Presidio engines.")
            self._available = False

    @property
    def available(self) -> bool:
        """Return whether PII detection is operational."""
        return self._available

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self, text: str) -> list[dict[str, Any]]:
        """Detect PII entities in *text*.

        Parameters
        ----------
        text : str
            The text to scan.

        Returns
        -------
        list[dict]
            Each dict contains:
            - ``entity_type`` (str): e.g. ``"EMAIL_ADDRESS"``
            - ``start`` (int): character start offset
            - ``end`` (int): character end offset
            - ``score`` (float): confidence score
            - ``text`` (str): the matched substring
        """
        if not self._available or self._analyzer is None:
            return []

        try:
            results: list[RecognizerResult] = self._analyzer.analyze(
                text=text,
                entities=self._entities,
                language=self._language,
                score_threshold=self._score_threshold,
            )

            detections: list[dict[str, Any]] = []
            for result in results:
                detection = {
                    "entity_type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": round(result.score, 4),
                    "text": text[result.start : result.end],
                }
                detections.append(detection)

            if detections:
                logger.info(
                    "PII scan found %d entit%s: %s",
                    len(detections),
                    "y" if len(detections) == 1 else "ies",
                    ", ".join(
                        f"{d['entity_type']}({d['score']:.2f})"
                        for d in detections
                    ),
                )

            return detections

        except Exception:
            logger.exception("Error during PII scan.")
            return []

    # ------------------------------------------------------------------
    # Redact
    # ------------------------------------------------------------------

    def redact(self, text: str) -> str:
        """Replace PII in *text* with human-readable placeholders.

        Uses the placeholder map (e.g. ``EMAIL_ADDRESS`` -> ``[EMAIL]``).
        Entity types without an explicit mapping are replaced with
        ``[<ENTITY_TYPE>]``.

        Parameters
        ----------
        text : str
            The text to redact.

        Returns
        -------
        str
            The text with all detected PII replaced by placeholders.
        """
        if not self._available or self._analyzer is None or self._anonymizer is None:
            return text

        try:
            results: list[RecognizerResult] = self._analyzer.analyze(
                text=text,
                entities=self._entities,
                language=self._language,
                score_threshold=self._score_threshold,
            )

            if not results:
                return text

            # Build per-entity-type operator configs for replacement.
            operators: dict[str, OperatorConfig] = {}
            for result in results:
                etype = result.entity_type
                if etype not in operators:
                    placeholder = _PLACEHOLDER_MAP.get(etype, f"[{etype}]")
                    operators[etype] = OperatorConfig(
                        "replace", {"new_value": placeholder}
                    )

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=operators,
            )

            redacted_text: str = anonymized.text

            # Audit log: record what was redacted (entity types only, not values).
            entity_types_found = sorted({r.entity_type for r in results})
            logger.info(
                "PII redacted %d entit%s (%s) from text.",
                len(results),
                "y" if len(results) == 1 else "ies",
                ", ".join(entity_types_found),
            )

            return redacted_text

        except Exception:
            logger.exception("Error during PII redaction; returning original text.")
            return text
