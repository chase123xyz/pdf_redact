"""Configuration file handling and validation using Pydantic."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator
import yaml
from pathlib import Path


class ScaleRange(BaseModel):
    """Scale range for multi-scale template matching."""
    min: float = Field(default=0.5, ge=0.1, le=1.0, description="Minimum scale")
    max: float = Field(default=2.0, ge=1.0, le=5.0, description="Maximum scale")
    step: float = Field(default=0.1, gt=0, le=0.5, description="Scale increment")


class ZoneFilter(BaseModel):
    """Zone filtering configuration."""
    include: List[str] = Field(default_factory=lambda: ["header", "footer", "body"])
    exclude: List[str] = Field(default_factory=list)


class FontCriteria(BaseModel):
    """Font-based filtering criteria."""
    min_size: Optional[int] = Field(default=8, description="Minimum font size in points")
    max_size: Optional[int] = Field(default=14, description="Maximum font size in points")
    exclude_fonts: List[str] = Field(default_factory=list, description="Fonts to never redact")


class TextPattern(BaseModel):
    """Configuration for a text redaction pattern."""
    pattern: str = Field(..., description="Regex pattern or literal text to match")
    description: str = Field(..., description="Human-readable description")
    case_sensitive: bool = Field(default=False, description="Whether pattern matching is case-sensitive")
    whole_words_only: bool = Field(default=False, description="Only match complete words")

    # Advanced options (optional)
    context_keywords: List[str] = Field(default_factory=list, description="Keywords indicating redactable context")
    proximity_threshold: int = Field(default=150, ge=10, le=1000, description="Proximity radius in pixels")
    exclude_if_near: List[str] = Field(default_factory=list, description="Keywords preventing redaction")


class LogoTemplate(BaseModel):
    """Configuration for a logo template."""
    name: str = Field(..., description="Template identifier")
    image_path: str = Field(..., description="Path to reference image")
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Matching confidence threshold")
    scale_range: ScaleRange = Field(default_factory=ScaleRange)
    method: str = Field(default="cv2.TM_CCOEFF_NORMED", description="OpenCV matching method")

    @field_validator('image_path')
    @classmethod
    def validate_image_path(cls, v):
        # Just store the path, we'll validate existence at runtime
        return v


class FontHeuristics(BaseModel):
    """Font-based classification heuristics."""
    annotation_fonts: List[str] = Field(
        default_factory=lambda: ["Arial", "Helvetica", "Times", "TimesNewRoman", "Calibri"]
    )
    technical_fonts: List[str] = Field(
        default_factory=lambda: ["CourierNew", "Courier", "Monaco", "ISOCP", "ISOCPEUR", "TechnicBold"]
    )
    annotation_size_range: List[int] = Field(default_factory=lambda: [8, 14])
    technical_label_size_range: List[int] = Field(default_factory=lambda: [6, 10])


class ZoneDefinition(BaseModel):
    """Page zone definition in percentages."""
    top_percent: float = Field(default=0, ge=0, le=100)
    bottom_percent: float = Field(default=100, ge=0, le=100)
    left_percent: Optional[float] = Field(default=None, ge=0, le=100)
    right_percent: Optional[float] = Field(default=None, ge=0, le=100)


class ZoneDefinitions(BaseModel):
    """All page zone definitions."""
    header: ZoneDefinition = Field(default_factory=lambda: ZoneDefinition(top_percent=0, bottom_percent=15))
    footer: ZoneDefinition = Field(default_factory=lambda: ZoneDefinition(top_percent=85, bottom_percent=100))
    title_block: ZoneDefinition = Field(
        default_factory=lambda: ZoneDefinition(top_percent=85, bottom_percent=100, left_percent=60, right_percent=100)
    )


class ContextRules(BaseModel):
    """Context analysis configuration."""
    address_indicators: List[str] = Field(
        default_factory=lambda: ["Address", "Street", "City", "State", "ZIP", "Postal Code", "Location", "Ship to", "Bill to"]
    )
    schematic_indicators: List[str] = Field(
        default_factory=lambda: ["Scale", "Drawing", "Detail", "Section", "Dimension", "Note", "View", "Sheet", "Revision", "DWG"]
    )
    font_heuristics: FontHeuristics = Field(default_factory=FontHeuristics)
    zone_definitions: ZoneDefinitions = Field(default_factory=ZoneDefinitions)


class OutputSettings(BaseModel):
    """PDF output settings."""
    preserve_metadata: bool = Field(default=False, description="Keep PDF metadata")
    compress: bool = Field(default=True, description="Compress output PDF")
    linearize: bool = Field(default=True, description="Optimize for web viewing")


class ProcessingSettings(BaseModel):
    """Processing configuration."""
    render_dpi: int = Field(default=300, ge=72, le=600, description="DPI for PDF rendering")
    max_workers: int = Field(default=4, ge=1, le=32, description="Parallel processing workers")
    redaction_color: List[int] = Field(default_factory=lambda: [255, 255, 255], description="RGB color for redactions")
    output: OutputSettings = Field(default_factory=OutputSettings)

    @field_validator('redaction_color')
    @classmethod
    def validate_redaction_color(cls, v):
        if len(v) != 3:
            raise ValueError("redaction_color must be RGB list with 3 values")
        if not all(0 <= c <= 255 for c in v):
            raise ValueError("RGB values must be 0-255")
        return v


class ReportingSettings(BaseModel):
    """Reporting configuration."""
    generate_report: bool = Field(default=True, description="Generate redaction report")
    report_format: str = Field(default="json", description="Report format")
    include_coordinates: bool = Field(default=True, description="Include bbox coordinates")
    include_preview_images: bool = Field(default=False, description="Save preview images")
    report_filename: str = Field(default="redaction_report.json", description="Report filename")

    @field_validator('report_format')
    @classmethod
    def validate_report_format(cls, v):
        allowed = ['json', 'html', 'txt']
        if v not in allowed:
            raise ValueError(f"report_format must be one of {allowed}")
        return v


class PIIRedactionConfig(BaseModel):
    """PII (Personally Identifiable Information) redaction configuration."""
    # Common PII types
    redact_emails: bool = Field(default=False, description="Redact email addresses")
    redact_phone_numbers: bool = Field(default=False, description="Redact phone numbers")
    redact_addresses: bool = Field(default=False, description="Redact addresses")
    redact_names: bool = Field(default=False, description="Redact person names")
    redact_ssn: bool = Field(default=False, description="Redact Social Security Numbers")

    # Custom patterns
    custom_names: List[str] = Field(default_factory=list, description="Specific names to redact")
    custom_patterns: List[TextPattern] = Field(default_factory=list, description="Custom text patterns to redact")


class TextRedactionConfig(BaseModel):
    """Text redaction configuration."""
    pii: PIIRedactionConfig = Field(default_factory=PIIRedactionConfig)
    patterns: List[TextPattern] = Field(default_factory=list)


class LogoRedactionConfig(BaseModel):
    """Logo redaction configuration."""
    templates: List[LogoTemplate] = Field(default_factory=list)


class RedactionConfig(BaseModel):
    """Root configuration model."""
    version: str = Field(default="1.0", description="Config format version")
    text_redaction: TextRedactionConfig = Field(default_factory=TextRedactionConfig)
    logo_redaction: LogoRedactionConfig = Field(default_factory=LogoRedactionConfig)
    context_rules: ContextRules = Field(default_factory=ContextRules)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    reporting: ReportingSettings = Field(default_factory=ReportingSettings)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'RedactionConfig':
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, yaml_path: str) -> None:
        """Save configuration to YAML file."""
        with open(yaml_path, 'w') as f:
            # Convert to dict and dump
            data = self.model_dump(exclude_none=True)
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def create_default(cls) -> 'RedactionConfig':
        """Create a default configuration."""
        return cls()
