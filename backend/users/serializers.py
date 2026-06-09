from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("id", "email", "password", "password_confirm")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Adres email jest już zajęty.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Hasła nie są identyczne."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class MeSerializer(serializers.ModelSerializer):
    utworzono = serializers.DateTimeField(source="date_joined", read_only=True)
    liczba_grup = serializers.SerializerMethodField()
    liczba_aktywnych_alertow = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "utworzono", "liczba_grup", "liczba_aktywnych_alertow")
        read_only_fields = fields

    def get_liczba_grup(self, obj: Any) -> int:
        return obj.grupy.count()

    def get_liczba_aktywnych_alertow(self, obj: Any) -> int:
        if not hasattr(obj, "alerty"):
            return 0
        return obj.alerty.filter(aktywny=True).count()
