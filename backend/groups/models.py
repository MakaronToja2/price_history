from __future__ import annotations

from django.conf import settings
from django.db import models


class GrupaProduktow(models.Model):
    uzytkownik = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grupy",
    )
    nazwa = models.CharField(max_length=255)
    opis = models.TextField(blank=True)
    url_obrazka = models.TextField(blank=True)

    najnizsza_cena_globalna = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    najlepsza_platforma = models.CharField(max_length=100, blank=True)
    najlepszy_sprzedawca = models.CharField(max_length=255, blank=True)
    cena_docelowa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    aktywny = models.BooleanField(default=True)

    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "grupy_produktow"
        verbose_name = "grupa produktów"
        verbose_name_plural = "grupy produktów"
        ordering = ["-utworzono"]
        indexes = [
            models.Index(fields=["uzytkownik"], name="idx_grupy_uzytkownik"),
            models.Index(
                fields=["aktywny"],
                name="idx_grupy_aktywny",
                condition=models.Q(aktywny=True),
            ),
        ]

    def __str__(self) -> str:
        return self.nazwa
