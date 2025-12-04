"""Text redaction with context-aware filtering."""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pdf_redact.config import TextPattern, RedactionConfig


# Common PII regex patterns
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way)\b',
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
    """Handles text search and context-aware filtering for redaction."""

    def __init__(self, config: RedactionConfig):
        """
        Initialize the text redactor.

        Args:
            config: Redaction configuration
        """
        self.config = config
        self.context_analyzer = None  # Will be set by pdf_processor
        self.patterns = self._build_patterns()

    def set_context_analyzer(self, analyzer):
        """Set the context analyzer (to avoid circular imports)."""
        self.context_analyzer = analyzer

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

        # Add custom names as literal patterns
        for name in pii_config.custom_names:
            patterns.append(TextPattern(
                pattern=re.escape(name),
                description=f"Name: {name}",
                case_sensitive=False
            ))

        # Add custom patterns from config
        patterns.extend(pii_config.custom_patterns)

        # Add any legacy patterns from text_redaction.patterns
        patterns.extend(self.config.text_redaction.patterns)

        return patterns

    def find_redaction_areas(self, page: fitz.Page, patterns: List[TextPattern]) -> List[RedactionArea]:
        """
        Find all text areas that should be redacted on a page.

        Args:
            page: PDF page to search
            patterns: List of text patterns to search for

        Returns:
            List of redaction areas
        """
        all_redaction_areas = []

        for pattern in patterns:
            # Extract text instances matching the pattern
            instances = self.extract_text_instances(page, pattern.pattern)

            # Filter by context if context analyzer is available
            if self.context_analyzer:
                filtered_instances = self.filter_by_context(page, instances, pattern)
            else:
                # Without context analyzer, include all matches
                filtered_instances = instances

            # Convert to redaction areas
            for instance in filtered_instances:
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

    def extract_text_instances(self, page: fitz.Page, pattern: str) -> List[TextInstance]:
        """
        Extract all text instances matching the pattern.

        Args:
            page: PDF page
            pattern: Regex pattern or literal text

        Returns:
            List of text instances with metadata
        """
        instances = []

        try:
            # Try regex matching first
            regex = re.compile(pattern, re.IGNORECASE)
            is_regex = True
        except re.error:
            # If pattern is not valid regex, treat as literal
            is_regex = False

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
                        matches = list(regex.finditer(text))
                        if not matches:
                            continue

                        # For regex, we need to find bounding box of matched substring
                        # This is approximate - we'll use the whole span's bbox
                        for match in matches:
                            instance = TextInstance(
                                content=match.group(),
                                bbox=fitz.Rect(span["bbox"]),
                                page_number=page.number,
                                font_name=span.get("font", ""),
                                font_size=span.get("size", 0.0),
                                font_flags=span.get("flags", 0)
                            )
                            instances.append(instance)
                    else:
                        # Literal matching
                        if pattern.lower() in text.lower():
                            instance = TextInstance(
                                content=text,
                                bbox=fitz.Rect(span["bbox"]),
                                page_number=page.number,
                                font_name=span.get("font", ""),
                                font_size=span.get("size", 0.0),
                                font_flags=span.get("flags", 0)
                            )
                            instances.append(instance)

        # Also use search_for for additional coverage
        search_results = self._search_page(page, pattern, is_regex)
        for result in search_results:
            # Check if we already have this instance (avoid duplicates)
            is_duplicate = any(
                abs(inst.bbox.x0 - result.bbox.x0) < 1 and
                abs(inst.bbox.y0 - result.bbox.y0) < 1
                for inst in instances
            )
            if not is_duplicate:
                instances.append(result)

        return instances

    def _search_page(self, page: fitz.Page, pattern: str, is_regex: bool) -> List[TextInstance]:
        """
        Use PyMuPDF's search_for function for additional text finding.

        Args:
            page: PDF page
            pattern: Search pattern
            is_regex: Whether pattern is regex

        Returns:
            List of text instances
        """
        instances = []

        if is_regex:
            # PyMuPDF search doesn't support full regex, so we extract all text
            # and match manually - already handled in extract_text_instances
            return instances
        else:
            # Use built-in search for literal text
            text_instances = page.search_for(pattern)
            for rect in text_instances:
                instance = TextInstance(
                    content=pattern,
                    bbox=rect,
                    page_number=page.number,
                    font_name="",  # search_for doesn't provide font info
                    font_size=0.0
                )
                instances.append(instance)

        return instances

    def filter_by_context(
        self,
        page: fitz.Page,
        instances: List[TextInstance],
        pattern: TextPattern
    ) -> List[TextInstance]:
        """
        Filter text instances based on context analysis.

        Args:
            page: PDF page
            instances: Text instances to filter
            pattern: Pattern configuration with context rules

        Returns:
            Filtered list of instances that should be redacted
        """
        if not self.context_analyzer:
            return instances

        filtered = []

        for instance in instances:
            # Check if this instance should be redacted based on context
            should_redact = self.context_analyzer.is_in_redactable_context(
                page, instance, pattern
            )

            if should_redact:
                filtered.append(instance)

        return filtered
