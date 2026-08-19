from setuptools import setup, find_packages

setup(
    name="rambo-py",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "rambo-py=rambo_py.main:main",
        ],
    },
)
