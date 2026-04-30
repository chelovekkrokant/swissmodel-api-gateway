from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 10002
    swissmodel_api_key: str
    base_url: str = "https://swissmodel.expasy.org"
    max_wait_time: int = 3600
    poll_interval: int = 10

    project_create_url: str = "https://swissmodel.expasy.org/automodel"
    template_upload_url: str = "https://swissmodel.expasy.org/user_template"
    project_status_url: str = "https://swissmodel.expasy.org/project/{project_id}/models/summary/"

    class Config:
        env_file = ".env"


settings = Settings()