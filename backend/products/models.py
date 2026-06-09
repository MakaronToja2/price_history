from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Platforma(models.Model):
    NAZWA_ALLEGRO = "allegro"
    NAZWA_AMAZON = "amazon"

    TYP_API = "api"
    TYP_WEB = "web"
    TYP_SCRAPERA_CHOICES = [
        (TYP_API, "API"),
        (TYP_WEB, "Web scraping"),
    ]

    nazwa = models.CharField(max_length=100, unique=True)
    bazowy_url = models.CharField(max_length=255, blank=True)
    typ_scrapera = models.CharField(max_length=20, choices=TYP_SCRAPERA_CHOICES)

    class Meta:
        db_table = "platformy"
        verbose_name = "platforma"
        verbose_name_plural = "platformy"
        ordering = ["nazwa"]

    def __str__(self) -> str:
        return self.nazwa


class Produkt(models.Model):
    grupa = models.ForeignKey(
        "groups.GrupaProduktow",
        on_delete=models.CASCADE,
        related_name="produkty",
    )
    platforma = models.ForeignKey(
        Platforma,
        on_delete=models.PROTECT,
        related_name="produkty",
    )
    zewnetrzny_id = models.CharField(max_length=255)
    url = models.TextField()
    nazwa = models.CharField(max_length=500, blank=True)
    url_obrazka = models.TextField(blank=True)
    aktywny = models.BooleanField(default=True)

    wskaznik_zmiennosci = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.5"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    interwal_sprawdzania_min = models.PositiveIntegerField(default=360)
    ostatnie_sprawdzenie = models.DateTimeField(null=True, blank=True)
    nastepne_sprawdzenie = models.DateTimeField(null=True, blank=True)

    aktualna_najnizsza_cena = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    aktualny_najlepszy_sprzedawca = models.CharField(max_length=255, blank=True)
    srednia_cena_30d = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    odchylenie_std_30d = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    liczba_sprzedawcow = models.PositiveIntegerField(default=0)

    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "produkty"
        verbose_name = "produkt"
        verbose_name_plural = "produkty"
        constraints = [
            models.UniqueConstraint(
                fields=["grupa", "platforma", "zewnetrzny_id"],
                name="unique_produkt_per_platforma_w_grupie",
            ),
            models.CheckConstraint(
                condition=models.Q(wskaznik_zmiennosci__gte=0)
                & models.Q(wskaznik_zmiennosci__lte=1),
                name="wskaznik_zmiennosci_w_zakresie",
            ),
        ]
        indexes = [
            models.Index(fields=["grupa"]),
            models.Index(fields=["platforma"]),
            models.Index(fields=["nastepne_sprawdzenie"], name="idx_produkty_polling"),
            models.Index(fields=["wskaznik_zmiennosci"], name="idx_produkty_volatility"),
        ]

    def __str__(self) -> str:
        return f"{self.platforma.nazwa}:{self.zewnetrzny_id}"
