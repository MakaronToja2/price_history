from django.db import migrations

CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS historia_cen (
    czas        TIMESTAMPTZ NOT NULL,
    produkt_id  INTEGER     NOT NULL,
    sprzedawca_id INTEGER,
    cena        NUMERIC(10, 2) NOT NULL,
    waluta      VARCHAR(3)  NOT NULL DEFAULT 'PLN',
    jest_najnizsza BOOLEAN  NOT NULL DEFAULT FALSE
);

SELECT create_hypertable(
    'historia_cen',
    'czas',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_historia_cen_produkt
    ON historia_cen (produkt_id, czas DESC);

CREATE INDEX IF NOT EXISTS idx_historia_cen_sprzedawca
    ON historia_cen (sprzedawca_id, produkt_id, czas DESC);

CREATE INDEX IF NOT EXISTS idx_historia_cen_najnizsza
    ON historia_cen (produkt_id, czas DESC)
    WHERE jest_najnizsza = TRUE;
"""

REVERSE_SQL = "DROP TABLE IF EXISTS historia_cen CASCADE;"


class Migration(migrations.Migration):
    initial = True
    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(sql=CREATE_SQL, reverse_sql=REVERSE_SQL),
    ]
