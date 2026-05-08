from setuptools import setup, find_packages

setup(
    name="ai_core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "httpx>=0.25.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "redis>=5.0.0",
        "openai>=1.0.0",
        "anthropic>=0.8.0",
    ],
)