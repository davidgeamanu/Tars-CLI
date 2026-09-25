from setuptools import setup, find_packages

setup(
    name="tars",
    version="2.0.0",
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
