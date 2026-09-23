"""Central config. All defaults are DUMMY synthetic values only."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str = "dummy_groq_key_replace_me"
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    MONGO_URI: str = "mongodb://localhost:27017/demo_lab"
    CHROMA_DIR: str = "./data/chroma"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
