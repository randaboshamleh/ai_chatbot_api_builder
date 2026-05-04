import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import TenantUser

from .serializers import LoginSerializer, TenantRegistrationSerializer, UserSerializer

logger = logging.getLogger(__name__)


def _resolve_login_user(identifier: str, password: str) -> tuple[TenantUser | None, str | None]:
    """
    Resolve user by username first, then by email.
    Handles duplicate emails deterministically by checking password match count.
    """
    value = (identifier or "").strip()
    if not value:
        return None, "invalid"

    # Username path (exact match)
    user = TenantUser.objects.filter(username=value).first()
    if user:
        if user.check_password(password):
            return user, None
        return None, "invalid"

    # Email path (case-insensitive)
    candidates = list(TenantUser.objects.filter(email__iexact=value.lower()))
    if not candidates:
        return None, "invalid"

    matched = [candidate for candidate in candidates if candidate.check_password(password)]
    if len(matched) == 1:
        return matched[0], None
    if len(matched) > 1:
        return None, "ambiguous_email"
    return None, "invalid"


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TenantRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "message": "Registration completed successfully.",
                "access": result["access"],
                "refresh": result["refresh"],
                "user": UserSerializer(result["user"]).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            logger.info(f"Login attempt - Request data: {request.data}")
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            identifier = serializer.validated_data["identifier"]
            password = serializer.validated_data["password"]
            logger.info(f"Login attempt - Identifier: {identifier}, Password length: {len(password)}")
            
            user, error_code = _resolve_login_user(identifier, password)
            logger.info(f"Login attempt - User found: {user is not None}, Error code: {error_code}")

            if error_code == "ambiguous_email":
                logger.warning(f"Login failed - Ambiguous email: {identifier}")
                return Response(
                    {"error": "Multiple accounts share this email. Please login using username."},
                    status=status.HTTP_409_CONFLICT,
                )

            if not user:
                logger.warning(f"Login failed - Invalid credentials for: {identifier}")
                return Response(
                    {"error": "Invalid username/email or password."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.tenant_id:
                logger.warning(f"Login failed - No tenant for user: {identifier}")
                return Response(
                    {"error": "This account is not linked to a tenant workspace. Please register a tenant account."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            logger.info(f"Login successful - User: {user.username}, Email: {user.email}")
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                }
            )
        except Exception as exc:
            logger.error(f"Login error - Exception: {exc}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred during login."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
        except Exception:
            pass
        return Response({"message": "Logged out successfully."})
