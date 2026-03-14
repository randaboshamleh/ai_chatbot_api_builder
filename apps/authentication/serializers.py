from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from apps.tenants.models import Tenant, TenantUser
import secrets


class TenantRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    slug = serializers.SlugField()
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_slug(self, value):
        if Tenant.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("هذا الـ subdomain مستخدم مسبقاً")
        return value

    def validate_username(self, value):
        if TenantUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("اسم المستخدم مستخدم مسبقاً")
        return value

    def create(self, validated_data):
        tenant = Tenant.objects.create(
            name=validated_data['company_name'],
            subdomain=validated_data['slug'],
            api_key=secrets.token_urlsafe(48),
        )
        user = TenantUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            tenant=tenant,
            role='owner',
        )
        refresh = RefreshToken.for_user(user)
        return {
            'tenant': tenant,
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = TenantUser
        fields = ['id', 'username', 'email', 'role', 'tenant_name']