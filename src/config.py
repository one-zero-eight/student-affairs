from pathlib import Path
from typing import Optional

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class AccountsSettings(BaseSettings):
    api_url: str
    api_jwt_token: SecretStr


class OmnideskSettings(BaseSettings):
    domain: str
    staff_email: str
    api_key: SecretStr
    jwt_marker: SecretStr

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}.omnidesk.ru/api"

    @property
    def jwt_access_base_url(self) -> str:
        return f"https://{self.domain}.omnidesk.ru/access/jwt"

    @property
    def default_redirect_to(self) -> str:
        return f"https://{self.domain}.omnidesk.ru/user/cases/"


class Settings(BaseSettings):
    accounts: Optional[AccountsSettings] = None
    omnidesk: OmnideskSettings
    app_root_path: str = ""
    'Prefix for the API path (e.g. "/api/v0")'
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


_settings_path = Path(__file__).parent.parent / "settings.yaml"
settings = Settings.from_yaml(_settings_path)
