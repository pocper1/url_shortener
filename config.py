from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    sqlalchemy_database_url: str = "sqlite:///./url_shortener.db"

    class Config:
        env_file = ".env"

settings = Settings()
