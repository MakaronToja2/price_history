from __future__ import annotations

from rest_framework import serializers

from products.models import Produkt

from .models import GrupaProduktow


class ProduktSummarySerializer(serializers.ModelSerializer):
    platforma = serializers.CharField(source="platforma.nazwa", read_only=True)

    class Meta:
        model = Produkt
        fields = (
            "id",
            "platforma",
            "nazwa",
            "url",
            "aktualna_najnizsza_cena",
            "aktualny_najlepszy_sprzedawca",
            "wskaznik_zmiennosci",
            "liczba_sprzedawcow",
            "ostatnie_sprawdzenie",
        )
        read_only_fields = fields


class GrupaListSerializer(serializers.ModelSerializer):
    liczba_produktow = serializers.IntegerField(read_only=True)

    class Meta:
        model = GrupaProduktow
        fields = (
            "id",
            "nazwa",
            "opis",
            "url_obrazka",
            "najnizsza_cena_globalna",
            "najlepsza_platforma",
            "najlepszy_sprzedawca",
            "cena_docelowa",
            "aktywny",
            "liczba_produktow",
            "utworzono",
        )
        read_only_fields = (
            "id",
            "url_obrazka",
            "najnizsza_cena_globalna",
            "najlepsza_platforma",
            "najlepszy_sprzedawca",
            "liczba_produktow",
            "utworzono",
        )


class GrupaDetailSerializer(serializers.ModelSerializer):
    produkty = ProduktSummarySerializer(many=True, read_only=True)

    class Meta:
        model = GrupaProduktow
        fields = (
            "id",
            "nazwa",
            "opis",
            "url_obrazka",
            "najnizsza_cena_globalna",
            "najlepsza_platforma",
            "najlepszy_sprzedawca",
            "cena_docelowa",
            "aktywny",
            "utworzono",
            "produkty",
        )
        read_only_fields = (
            "id",
            "url_obrazka",
            "najnizsza_cena_globalna",
            "najlepsza_platforma",
            "najlepszy_sprzedawca",
            "utworzono",
            "produkty",
        )
