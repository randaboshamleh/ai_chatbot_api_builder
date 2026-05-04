import secrets

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Tenant, TenantUser


class TenantRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    slug = serializers.SlugField()
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_slug(self, value):
        if Tenant.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("This subdomain is already in use.")
        return value

    def validate_username(self, value):
        if TenantUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def validate_email(self, value):
        normalized = (value or "").strip().lower()
        if TenantUser.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("This email is already in use.")
        return normalized

    def create(self, validated_data):
        tenant = Tenant.objects.create(
            name=validated_data["company_name"],
            subdomain=validated_data["slug"],
            api_key=secrets.token_urlsafe(48),
        )
        user = TenantUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            tenant=tenant,
            role="owner",
        )
        refresh = RefreshToken.for_user(user)
        return {
            "tenant": tenant,
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        identifier = attrs.get("email") or attrs.get("username")
        if not identifier or not str(identifier).strip():
            raise serializers.ValidationError("A username or email address is required for login.")

        attrs["identifier"] = str(identifier).strip()
        return attrs


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = TenantUser
        fields = ["id", "username", "email", "role", "tenant_name"]
