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

    rate_limit_max_retries: int = 5
    rate_limit_base_delay: float = 1.0
    rate_limit_max_delay: float = 60.0

    class Config:
        env_file = ".env"


settings = Settings()