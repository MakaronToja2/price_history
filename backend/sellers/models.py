from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Sprzedawca(models.Model):
    platforma = models.ForeignKey(
        "products.Platforma",
        on_delete=models.PROTECT,
        related_name="sprzedawcy",
    )
    zewnetrzny_id = models.CharField(max_length=255, blank=True)
    nazwa = models.CharField(max_length=255)
    url_profilu = models.TextField(blank=True)
    ocena = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("5"))],
    )
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sprzedawcy"
        verbose_name = "sprzedawca"
        verbose_name_plural = "sprzedawcy"
        constraints = [
            models.UniqueConstraint(
                fields=["platforma", "zewnetrzny_id"],
                name="unique_sprzedawca_per_platforma",
            ),
            models.CheckConstraint(
                condition=models.Q(ocena__isnull=True)
                | (models.Q(ocena__gte=0) & models.Q(ocena__lte=5)),
                name="ocena_w_zakresie",
            ),
        ]
        indexes = [
            models.Index(fields=["platforma"], name="idx_sprzedawcy_platforma"),
        ]

    def __str__(self) -> str:
        return f"{self.nazwa} ({self.platforma.nazwa})"
