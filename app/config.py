from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 10002
    api_key: str
    base_url: str
    automodel_url: str

    class Config:
        env_file = ".env"


settings = Settings()