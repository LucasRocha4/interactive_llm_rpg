import unittest
from pathlib import Path

from llm_interactive_rpg.config.database import database_settings


class TestDatabaseSettings(unittest.TestCase):
    def test_sqlite_usa_caminho_relativo_ao_projeto_django(self):
        base = Path("/projeto/llm_interactive_rpg")
        configuracao = database_settings("sqlite:///db.sqlite3", base)

        self.assertEqual(configuracao["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(configuracao["NAME"], base / "db.sqlite3")

    def test_postgresql_e_configuravel_por_url(self):
        configuracao = database_settings(
            "postgresql://usuario:senha@servidor:5433/rpg?sslmode=require",
            Path("/projeto/llm_interactive_rpg"),
        )

        self.assertEqual(configuracao["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(configuracao["NAME"], "rpg")
        self.assertEqual(configuracao["USER"], "usuario")
        self.assertEqual(configuracao["OPTIONS"], {"sslmode": "require"})
