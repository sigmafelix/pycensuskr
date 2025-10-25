"""
Setup script for pycensuskr package.
For modern Python packaging, pyproject.toml is preferred.
This file is kept for backward compatibility.
"""

from setuptools import setup, find_packages

# Read the contents of README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pycensuskr",
    version="{{VERSION_PLACEHOLDER}}",
    author="Insang Song",
    author_email="geoissong@snu.ac.kr",
    description="A Python package for Korean census data processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sigmafelix/pycensuskr",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={'pycensuskr': ['data/*']},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
)
