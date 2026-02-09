"""Configuration file handling and validation using Pydantic."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import yaml
from pathlib import Path


class ScaleRange(BaseModel):
    """Scale range for multi-scale template matching."""
    min: float = Field(default=0.5, ge=0.1, le=5.0, description="Minimum scale")
    max: float = Field(default=3.0, ge=0.1, le=10.0, description="Maximum scale")
    step: float = Field(default=0.1, gt=0, le=1.0, description="Scale increment")


class TextPattern(BaseModel):
    """Configuration for a text redaction pattern."""
    pattern: str = Field(..., description="Regex pattern or literal text to match")
    description: str = Field(..., description="Human-readable description")
    case_sensitive: bool = Field(default=False, description="Whether pattern matching is case-sensitive")
    whole_words_only: bool = Field(default=False, description="Only match complete words")


class LogoTemplate(BaseModel):
    """Configuration for a logo template."""
    name: str = Field(..., description="Template identifier")
    image_path: str = Field(..., description="Path to reference image")
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Matching confidence threshold")
    scale_range: ScaleRange = Field(default_factory=ScaleRange)
    method: str = Field(default="cv2.TM_CCOEFF_NORMED", description="OpenCV matching method")

    @field_validator('image_path')
    @classmethod
    def validate_image_path(cls, v):
        # Just store the path, we'll validate existence at runtime
        return v


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
    custom_names: List[str] = Field(default_factory=list, description="Specific names to redact (words only)")
    custom_textbox_matches: List[str] = Field(default_factory=list, description="Text to find and redact entire containing textbox")
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
    model_config = {"extra": "ignore"}

    version: str = Field(default="1.0", description="Config format version")
    text_redaction: TextRedactionConfig = Field(default_factory=TextRedactionConfig)
    logo_redaction: LogoRedactionConfig = Field(default_factory=LogoRedactionConfig)
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
