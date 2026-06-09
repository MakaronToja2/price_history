from __future__ import annotations

from django.db import models


class HistoriaCen(models.Model):
    """Punkt w czasie ceny dla pary (produkt, sprzedawca).

    Stored in the `timeseries` database as a TimescaleDB hypertable
    partitioned on `czas`. The table has no primary key (TimescaleDB
    requires the partitioning column in any unique index, which conflicts
    with Django's default `id` PK), so writes go through `HistoriaCenRepository`
    rather than the ORM.
    """

    czas = models.DateTimeField(primary_key=True)
    produkt_id = models.IntegerField()
    sprzedawca_id = models.IntegerField(null=True, blank=True)
    cena = models.DecimalField(max_digits=10, decimal_places=2)
    waluta = models.CharField(max_length=3, default="PLN")
    jest_najnizsza = models.BooleanField(default=False)

    class Meta:
        db_table = "historia_cen"
        managed = False
        verbose_name = "historia cen"
        verbose_name_plural = "historia cen"

    def __str__(self) -> str:
        return f"produkt={self.produkt_id} czas={self.czas.isoformat()} cena={self.cena}"
