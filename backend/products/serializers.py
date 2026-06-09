from __future__ import annotations

from rest_framework import serializers

from .models import Produkt


class ProduktSerializer(serializers.ModelSerializer):
    platforma = serializers.CharField(source="platforma.nazwa", read_only=True)
    grupa_id = serializers.IntegerField(source="grupa.id", read_only=True)
    task_id = serializers.CharField(read_only=True)

    class Meta:
        model = Produkt
        fields = (
            "id",
            "grupa_id",
            "platforma",
            "zewnetrzny_id",
            "nazwa",
            "url",
            "aktywny",
            "ostatnie_sprawdzenie",
            "task_id",
        )
        read_only_fields = (
            "id",
            "grupa_id",
            "platforma",
            "zewnetrzny_id",
            "nazwa",
            "aktywny",
            "ostatnie_sprawdzenie",
            "task_id",
        )


class AddProductSerializer(serializers.Serializer):
    url = serializers.URLField()
