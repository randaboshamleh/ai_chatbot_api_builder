from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.tenants.models import TenantUser
from .serializers import TenantRegistrationSerializer, LoginSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TenantRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            'message': 'تم تسجيل الشركة بنجاح',
            'access': result['access'],
            'refresh': result['refresh'],
            'user': UserSerializer(result['user']).data,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            username_or_email = serializer.validated_data['username']
            password = serializer.validated_data['password']

            # Try to find user by username or email
            user = TenantUser.objects.filter(username=username_or_email).first()
            if not user:
                user = TenantUser.objects.filter(email=username_or_email).first()

            if not user or not user.check_password(password):
                return Response(
                    {'error': 'بيانات الدخول غير صحيحة'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.tenant_id:
                return Response(
                    {'error': 'This account is not linked to a tenant workspace. Please register a new tenant account.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Login error: {str(e)}")
            return Response(
                {'error': 'حدث خطأ في تسجيل الدخول'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
        except Exception:
            pass
        return Response({'message': 'تم تسجيل الخروج'})
