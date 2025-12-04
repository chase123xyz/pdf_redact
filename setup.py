from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

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
        "tqdm>=4.65.0",
        "colorama>=0.4.6",
    ],
    entry_points={
        "console_scripts": [
            "pdf-redact=pdf_redact.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "pdf_redact": ["templates/*.yaml"],
    },
)
