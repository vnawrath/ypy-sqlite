from setuptools import setup, find_packages

setup(
    name="ypy-sqlite",
    version="0.1.0",
    description="SQLite persistence provider for YPY (Python bindings for YJS)",
    author="",
    author_email="",
    url="",
    packages=find_packages(),
    install_requires=[
        "y-py>=0.6.2",
        "aiosqlite>=0.18.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
)