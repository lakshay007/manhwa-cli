from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="manhwa-cli",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "manhwa-cli=manhwa_cli.cli:main",
        ],
    },
    author="Manhwa CLI Team",
    description="A CLI tool to browse and read manhwas from toonily.com",
    keywords="manhwa, manga, cli, comic, toonily",
    python_requires=">=3.6",
) 