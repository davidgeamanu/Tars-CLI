from setuptools import setup

setup(
    name="icarus",
    version="2.0.0",
    py_modules=["icarus"],
    install_requires=["rich>=13.0"],
    entry_points={
        "console_scripts": ["icarus=icarus:main"],
    },
)
