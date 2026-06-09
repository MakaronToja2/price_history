from __future__ import annotations

from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    grupa_id = serializers.IntegerField(source="grupa.id", read_only=True)
    grupa_nazwa = serializers.CharField(source="grupa.nazwa", read_only=True)

    class Meta:
        model = Alert
        fields = (
            "id",
            "grupa_id",
            "grupa_nazwa",
            "typ_alertu",
            "prog_ceny",
            "prog_procent",
            "aktywny",
            "ostatnie_wyzwolenie",
            "utworzono",
        )
        read_only_fields = (
            "id",
            "grupa_id",
            "grupa_nazwa",
            "ostatnie_wyzwolenie",
            "utworzono",
        )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        typ = attrs.get("typ_alertu", getattr(self.instance, "typ_alertu", None))
        prog_ceny = attrs.get("prog_ceny", getattr(self.instance, "prog_ceny", None))
        prog_procent = attrs.get("prog_procent", getattr(self.instance, "prog_procent", None))

        if typ == Alert.TYP_DOCELOWY and prog_ceny is None:
            raise serializers.ValidationError({"prog_ceny": "Wymagane dla typu 'docelowy'."})
        if typ == Alert.TYP_SPADEK_CENY and prog_procent is None:
            raise serializers.ValidationError({"prog_procent": "Wymagane dla typu 'spadek_ceny'."})
        return attrs
