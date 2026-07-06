"""Punto de entrada: credenciales solo desde variables de entorno."""

from __future__ import annotations

import os

from app.config import Settings


def main() -> None:
    settings = Settings.from_env()
    print(f"API URL: {settings.api_url}")
    print("Token cargado desde entorno (no hardcodeado).")


if __name__ == "__main__":
    main()
