"""Configuracion segura: sin secretos en codigo."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_url: str
    api_token: str

    @classmethod
    def from_env(cls) -> "Settings":
        api_url = os.environ.get("API_URL", "http://localhost:8080")
        api_token = os.environ.get("API_TOKEN", "")
        if not api_token:
            raise RuntimeError("Definir API_TOKEN en .env (ver .env.example)")
        return cls(api_url=api_url, api_token=api_token)
