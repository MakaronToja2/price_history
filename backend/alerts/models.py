from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Alert(models.Model):
    TYP_DOCELOWY = "docelowy"
    TYP_SPADEK_CENY = "spadek_ceny"
    TYP_FLASH_SALE = "flash_sale"

    TYP_CHOICES = [
        (TYP_DOCELOWY, "Cena docelowa"),
        (TYP_SPADEK_CENY, "Procentowy spadek ceny"),
        (TYP_FLASH_SALE, "Flash sale (auto)"),
    ]

    grupa = models.ForeignKey(
        "groups.GrupaProduktow",
        on_delete=models.CASCADE,
        related_name="alerty",
    )
    typ_alertu = models.CharField(max_length=20, choices=TYP_CHOICES)
    prog_ceny = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    prog_procent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    aktywny = models.BooleanField(default=True)
    ostatnie_wyzwolenie = models.DateTimeField(null=True, blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerty"
        verbose_name = "alert"
        verbose_name_plural = "alerty"
        ordering = ["-utworzono"]
        indexes = [
            models.Index(fields=["grupa"], name="idx_alerty_grupa"),
            models.Index(
                fields=["aktywny"],
                name="idx_alerty_aktywne",
                condition=models.Q(aktywny=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.typ_alertu} dla {self.grupa_id}"
