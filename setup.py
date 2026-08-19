from setuptools import setup, find_packages

setup(
    name="aegis",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "aegis=aegis.main:main",
            "aegis-gui=aegis.gui.app:run_gui",
        ],
    },
)
