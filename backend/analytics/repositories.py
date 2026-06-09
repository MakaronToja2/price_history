from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import connections


@dataclass(frozen=True, slots=True)
class PomiarCeny:
    """Single price observation produced by a scraper fetch."""

    czas: datetime
    produkt_id: int
    cena: Decimal
    sprzedawca_id: int | None = None
    waluta: str = "PLN"


class HistoriaCenRepository:
    """Raw-SQL repository for the `historia_cen` hypertable (TimescaleDB).

    The hypertable has no primary key (TimescaleDB constraints conflict
    with Django's auto-id) so we bypass the ORM and run prepared statements
    against the `timeseries` database connection.
    """

    DATABASE_ALIAS = "timeseries"

    def _conn(self):
        return connections[self.DATABASE_ALIAS]

    def insert_pomiary(self, pomiary: list[PomiarCeny]) -> None:
        """Insert a batch of measurements; the lowest cena in each
        `(czas, produkt_id)` group is flagged `jest_najnizsza=TRUE`."""
        if not pomiary:
            return

        # Determine the lowest cena per (czas, produkt_id) group so we can
        # set jest_najnizsza correctly on insert.
        lowest_by_group: dict[tuple[datetime, int], Decimal] = {}
        for p in pomiary:
            key = (p.czas, p.produkt_id)
            if key not in lowest_by_group or p.cena < lowest_by_group[key]:
                lowest_by_group[key] = p.cena

        rows = [
            (
                p.czas,
                p.produkt_id,
                p.sprzedawca_id,
                p.cena,
                p.waluta,
                p.cena == lowest_by_group[(p.czas, p.produkt_id)],
            )
            for p in pomiary
        ]

        sql = (
            "INSERT INTO historia_cen "
            "(czas, produkt_id, sprzedawca_id, cena, waluta, jest_najnizsza) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        with self._conn().cursor() as cur:
            cur.executemany(sql, rows)

    def get_pomiary_for_produkt(
        self, *, produkt_id: int, limit: int = 1000
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT czas, produkt_id, sprzedawca_id, cena, waluta, jest_najnizsza "
            "FROM historia_cen WHERE produkt_id = %s "
            "ORDER BY czas DESC LIMIT %s"
        )
        return self._fetch(sql, [produkt_id, limit])

    def get_lowest_history(
        self,
        *,
        produkt_id: int,
        since: datetime,
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT czas, produkt_id, sprzedawca_id, cena, waluta, jest_najnizsza "
            "FROM historia_cen "
            "WHERE produkt_id = %s AND jest_najnizsza = TRUE AND czas >= %s "
            "ORDER BY czas DESC"
        )
        return self._fetch(sql, [produkt_id, since])

    def get_stats(
        self,
        *,
        produkt_id: int,
        since: datetime,
    ) -> dict[str, Any]:
        sql = (
            "SELECT COUNT(*) AS count, AVG(cena) AS avg, STDDEV(cena) AS stddev, "
            "MIN(cena) AS min, MAX(cena) AS max "
            "FROM historia_cen "
            "WHERE produkt_id = %s AND jest_najnizsza = TRUE AND czas >= %s"
        )
        with self._conn().cursor() as cur:
            cur.execute(sql, [produkt_id, since])
            row = cur.fetchone()

        count, avg, stddev, mn, mx = row
        return {
            "count": int(count or 0),
            "avg": avg,
            "stddev": stddev,
            "min": mn,
            "max": mx,
        }

    def truncate(self) -> None:
        with self._conn().cursor() as cur:
            cur.execute("TRUNCATE TABLE historia_cen")

    def _fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        with self._conn().cursor() as cur:
            cur.execute(sql, params)
            columns = [c[0] for c in cur.description]
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
