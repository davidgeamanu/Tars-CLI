from setuptools import setup, find_packages

setup(
    name="tars",
    version="2.0.0",
    packages=find_packages(),
    install_requires=["rich>=13.0"],
    entry_points={
        "console_scripts": ["tars=tars.cli:main"],
    },
)