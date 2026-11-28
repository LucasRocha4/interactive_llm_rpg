from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def database_settings(database_url: str | None, base_dir: Path) -> dict:
    """Converte DATABASE_URL em configuração Django para SQLite ou PostgreSQL."""
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }

    if database_url.startswith("sqlite:///"):
        caminho = unquote(database_url[len("sqlite:///"):])
        if caminho == ":memory:":
            nome = ":memory:"
        else:
            if len(caminho) >= 3 and caminho[0] == "/" and caminho[2] == ":":
                caminho = caminho[1:]
            nome = Path(caminho)
            if not nome.is_absolute():
                nome = base_dir / nome
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": nome}

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.path.strip("/"):
        raise ImproperlyConfigured(
            "DATABASE_URL deve usar sqlite:///caminho ou postgresql://usuario:senha@host/banco."
        )

    configuracao = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }
    opcoes = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if opcoes:
        configuracao["OPTIONS"] = opcoes
    return configuracao
