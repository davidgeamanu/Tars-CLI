import re
from pathlib import Path

from setuptools import setup, find_packages

# The version lives in tars/__init__.py so the app, the installer and pip agree on it
VERSION = re.search(
    r'__version__ = "(.+?)"',
    (Path(__file__).parent / "tars" / "__init__.py").read_text(encoding="utf-8"),
).group(1)

setup(
    name="tars",
    version=VERSION,
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.10",
    install_requires=["rich>=13.0"],
    extras_require={
        "ai": ["anthropic>=0.50.0"],
        "dev": ["pytest"],
    },
    entry_points={
        "console_scripts": ["tars=tars.cli:main"],
    },
)
