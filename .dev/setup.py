from pathlib import Path
from setuptools import setup, find_packages

readme_path = Path(__file__).parent.parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="pdf-redact",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Context-aware PDF redaction tool for industrial documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pdf-redact",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "PyMuPDF>=1.23.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "click>=8.1.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf-redact=pdf_redact.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pdf_redact": ["templates/*.yaml"],
    },
)
