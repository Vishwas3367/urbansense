from app.config import Settings


def test_settings_ignore_environment_values_used_only_by_database_services(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PASSWORD=database-service-password\n"
        "DATABASE_URL=postgresql+psycopg://localhost:5433/urbansense\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql+psycopg://localhost:5433/urbansense"
