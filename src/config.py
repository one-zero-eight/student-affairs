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

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}.omnidesk.ru/api"


class Settings(BaseSettings):
    accounts: Optional[AccountsSettings] = None
    omnidesk: OmnideskSettings

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


_settings_path = Path(__file__).parent.parent / "settings.yaml"
settings = Settings.from_yaml(_settings_path)
