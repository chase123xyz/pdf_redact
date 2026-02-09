"""Text redaction with pattern matching."""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from dataclasses import dataclass
from pdf_redact.config import TextPattern, RedactionConfig


# Common PII regex patterns
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    # Phone: more strict - requires common phone formats with actual phone separators or spacing
    # Matches: (555) 123-4567, 555-123-4567, 555.123.4567, 5551234567, +1-555-123-4567
    'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]([0-9]{3})[-.\s]([0-9]{4})\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    # Address: more strict - requires reasonable street name (at least 2 letters after the number)
    # and a space before the street type to avoid matching part numbers
    'address': r'\b\d+\s+[A-Za-z]{2,}[A-Za-z\s]*\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way)\b',
}


@dataclass
class TextInstance:
    """Represents a text instance found in a PDF with metadata."""
    content: str
    bbox: fitz.Rect
    page_number: int
    font_name: str = ""
    font_size: float = 0.0
    font_flags: int = 0  # Font flags (bold, italic, etc.)


@dataclass
class RedactionArea:
    """Represents an area to be redacted."""
    rect: fitz.Rect
    page_number: int
    redaction_type: str  # 'text' or 'logo'
    matched_pattern: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextRedactor:
    """Handles text search and filtering for redaction."""

    def __init__(self, config: RedactionConfig):
        self.config = config
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[TextPattern]:
        """Build list of patterns from configuration including PII patterns."""
        patterns = []

        # Add PII patterns if enabled
        pii_config = self.config.text_redaction.pii

        if pii_config.redact_emails:
            patterns.append(TextPattern(
                pattern=PII_PATTERNS['email'],
                description="Email addresses"
            ))

        if pii_config.redact_phone_numbers:
            patterns.append(TextPattern(
                pattern=PII_PATTERNS['phone'],
                description="Phone numbers"
            ))

        if pii_config.redact_ssn:
            patterns.append(TextPattern(
                pattern=PII_PATTERNS['ssn'],
                description="Social Security Numbers"
            ))

        if pii_config.redact_addresses:
            patterns.append(TextPattern(
                pattern=PII_PATTERNS['address'],
                description="Street addresses"
            ))

        # Add custom names as word-level patterns (redact only the word)
        for name in pii_config.custom_names:
            patterns.append(TextPattern(
                pattern=r'\b' + re.escape(name) + r'\b',
                description=f"Word: {name}",
                case_sensitive=False,
                whole_words_only=True  # This flag indicates word-level redaction
            ))

        # Add custom textbox matches (redact entire textbox containing the match)
        for text in pii_config.custom_textbox_matches:
            patterns.append(TextPattern(
                pattern=re.escape(text),
                description=f"Textbox containing: {text}",
                case_sensitive=False,
                whole_words_only=False  # This flag indicates textbox-level redaction
            ))

        # Add custom patterns from config
        patterns.extend(pii_config.custom_patterns)

        # Add any legacy patterns from text_redaction.patterns
        patterns.extend(self.config.text_redaction.patterns)

        return patterns

    def find_redaction_areas(self, page: fitz.Page, patterns: List[TextPattern]) -> List[RedactionArea]:
        """Find all text areas that should be redacted on a page."""
        all_redaction_areas = []

        for pattern in patterns:
            instances = self.extract_text_instances(page, pattern)

            for instance in instances:
                area = RedactionArea(
                    rect=instance.bbox,
                    page_number=instance.page_number,
                    redaction_type="text",
                    matched_pattern=pattern.description,
                    confidence=1.0,
                    metadata={
                        "pattern": pattern.pattern,
                        "content": instance.content,
                        "font": instance.font_name,
                        "font_size": instance.font_size
                    }
                )
                all_redaction_areas.append(area)

        return all_redaction_areas

    def extract_text_instances(self, page: fitz.Page, pattern: TextPattern) -> List[TextInstance]:
        """Extract all text instances matching the pattern."""
        try:
            regex = re.compile(pattern.pattern, re.IGNORECASE if not pattern.case_sensitive else 0)
            is_regex = True
        except re.error:
            is_regex = False

        # For word-level redaction, use word-based extraction for precise boundaries
        if pattern.whole_words_only:
            return self._extract_word_level(page, pattern.pattern, regex, is_regex)
        else:
            # For textbox-level redaction, use span-based extraction
            return self._extract_span_level(page, pattern.pattern, regex, is_regex)

    def _extract_word_level(self, page: fitz.Page, pattern_str: str, regex, is_regex: bool) -> List[TextInstance]:
        """Extract text with word-level precision."""
        instances = []

        # Get all words with their bounding boxes
        words = page.get_text("words")  # Returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)

        for word_info in words:
            if len(word_info) < 5:
                continue

            x0, y0, x1, y1, word_text = word_info[:5]

            # Check if this word matches the pattern
            if is_regex:
                if regex.search(word_text):
                    instance = TextInstance(
                        content=word_text,
                        bbox=fitz.Rect(x0, y0, x1, y1),
                        page_number=page.number,
                        font_name="",
                        font_size=0.0
                    )
                    instances.append(instance)
            else:
                # Case-insensitive literal match for whole word
                if pattern_str.lower() == word_text.lower():
                    instance = TextInstance(
                        content=word_text,
                        bbox=fitz.Rect(x0, y0, x1, y1),
                        page_number=page.number,
                        font_name="",
                        font_size=0.0
                    )
                    instances.append(instance)

        return instances

    def _extract_span_level(self, page: fitz.Page, pattern_str: str, regex, is_regex: bool) -> List[TextInstance]:
        """Extract text with span/textbox-level precision."""
        instances = []

        # Get all text with detailed information
        text_dict = page.get_text("dict")

        # Iterate through blocks, lines, and spans
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Skip non-text blocks
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text:
                        continue

                    # Check if text matches pattern
                    if is_regex:
                        if regex.search(text):
                            instance = TextInstance(
                                content=text,
                                bbox=fitz.Rect(span["bbox"]),
                                page_number=page.number,
                                font_name=span.get("font", ""),
                                font_size=span.get("size", 0.0),
                                font_flags=span.get("flags", 0)
                            )
                            instances.append(instance)
                    else:
                        # Literal matching - if pattern found anywhere in span, redact whole span
                        if pattern_str.lower() in text.lower():
                            instance = TextInstance(
                                content=text,
                                bbox=fitz.Rect(span["bbox"]),
                                page_number=page.number,
                                font_name=span.get("font", ""),
                                font_size=span.get("size", 0.0),
                                font_flags=span.get("flags", 0)
                            )
                            instances.append(instance)

        return instances
