"""
Real unit tests for the AI Chatbot platform.
Tests cover: Tenant model, TenantUser, Document model, QueryLog, and Auth serializers.
"""
import sys
from unittest.mock import MagicMock

# Mock heavy optional dependencies not available in CI
# (chromadb, langchain, sentence_transformers, etc.)
_MOCK_MODULES = [
    "chromadb", "chromadb.config",
    "sentence_transformers",
    "langchain", "langchain.text_splitter",
    "langchain_text_splitters",
    "langchain_community", "langchain_community.document_loaders",
    "langchain_core", "langchain_core.documents",
    "whisper", "torch", "PIL", "unstructured",
]
for _mod in _MOCK_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenants.models import Tenant, TenantUser
from apps.documents.models import Document
from apps.analytics.models import QueryLog, DailyStats
from apps.authentication.serializers import TenantRegistrationSerializer


# ─────────────────────────────────────────────
# Tenant Model Tests
# ─────────────────────────────────────────────

class TenantModelTest(TestCase):

    def test_tenant_api_key_auto_generated(self):
        """Tenant.api_key is auto-generated on save if not provided."""
        tenant = Tenant.objects.create(name="Acme Corp", subdomain="acme")
        self.assertTrue(len(tenant.api_key) > 0)

    def test_tenant_api_key_unique(self):
        """Two tenants must have different api_keys."""
        t1 = Tenant.objects.create(name="Corp A", subdomain="corp-a")
        t2 = Tenant.objects.create(name="Corp B", subdomain="corp-b")
        self.assertNotEqual(t1.api_key, t2.api_key)

    def test_tenant_subdomain_unique(self):
        """Duplicate subdomain must raise an IntegrityError."""
        Tenant.objects.create(name="First", subdomain="unique-slug")
        with self.assertRaises(Exception):
            Tenant.objects.create(name="Second", subdomain="unique-slug")

    def test_tenant_default_plan_is_free(self):
        """Default plan for a new tenant is 'free'."""
        tenant = Tenant.objects.create(name="Free Co", subdomain="free-co")
        self.assertEqual(tenant.plan, "free")

    def test_tenant_str(self):
        """__str__ returns the tenant name."""
        tenant = Tenant.objects.create(name="My Company", subdomain="my-company")
        self.assertEqual(str(tenant), "My Company")

    def test_tenant_default_limits(self):
        """Default document and query limits are set correctly."""
        tenant = Tenant.objects.create(name="Limits Co", subdomain="limits-co")
        self.assertEqual(tenant.max_documents, 100)
        self.assertEqual(tenant.max_queries_per_day, 1000)
        self.assertEqual(tenant.max_users, 5)

    def test_tenant_is_active_by_default(self):
        """New tenants are active by default."""
        tenant = Tenant.objects.create(name="Active Co", subdomain="active-co")
        self.assertTrue(tenant.is_active)


# ─────────────────────────────────────────────
# TenantUser Model Tests
# ─────────────────────────────────────────────

class TenantUserModelTest(TestCase):

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Org", subdomain="test-org")

    def test_create_user_with_tenant(self):
        """User is correctly linked to a tenant."""
        user = TenantUser.objects.create_user(
            username="john",
            email="john@test.com",
            password="securepass123",
            tenant=self.tenant,
            role="member",
        )
        self.assertEqual(user.tenant, self.tenant)
        self.assertEqual(user.role, "member")

    def test_is_admin_or_owner_true_for_owner(self):
        """is_admin_or_owner() returns True for owner role."""
        user = TenantUser.objects.create_user(
            username="owner1", password="pass1234", tenant=self.tenant, role="owner"
        )
        self.assertTrue(user.is_admin_or_owner())

    def test_is_admin_or_owner_true_for_admin(self):
        """is_admin_or_owner() returns True for admin role."""
        user = TenantUser.objects.create_user(
            username="admin1", password="pass1234", tenant=self.tenant, role="admin"
        )
        self.assertTrue(user.is_admin_or_owner())

    def test_is_admin_or_owner_false_for_member(self):
        """is_admin_or_owner() returns False for member role."""
        user = TenantUser.objects.create_user(
            username="member1", password="pass1234", tenant=self.tenant, role="member"
        )
        self.assertFalse(user.is_admin_or_owner())

    def test_user_password_is_hashed(self):
        """Stored password must not be plain text."""
        user = TenantUser.objects.create_user(
            username="hashtest", password="plainpassword", tenant=self.tenant
        )
        self.assertNotEqual(user.password, "plainpassword")
        self.assertTrue(user.check_password("plainpassword"))


# ─────────────────────────────────────────────
# Registration Serializer Tests
# ─────────────────────────────────────────────

class RegistrationSerializerTest(TestCase):

    def _valid_data(self, suffix=""):
        return {
            "company_name": f"Test Company{suffix}",
            "slug": f"test-company{suffix}",
            "username": f"testuser{suffix}",
            "email": f"test{suffix}@example.com",
            "password": "strongpass123",
        }

    def test_valid_registration_creates_tenant_and_user(self):
        """Valid data creates a Tenant and TenantUser and returns tokens."""
        serializer = TenantRegistrationSerializer(data=self._valid_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save()
        self.assertIn("access", result)
        self.assertIn("refresh", result)
        self.assertIsInstance(result["tenant"], Tenant)
        self.assertIsInstance(result["user"], TenantUser)

    def test_duplicate_slug_is_rejected(self):
        """Registering with an existing subdomain must fail validation."""
        serializer = TenantRegistrationSerializer(data=self._valid_data("-dup"))
        serializer.is_valid()
        serializer.save()
        # Try same slug again
        serializer2 = TenantRegistrationSerializer(data=self._valid_data("-dup"))
        self.assertFalse(serializer2.is_valid())
        self.assertIn("slug", serializer2.errors)

    def test_duplicate_username_is_rejected(self):
        """Registering with an existing username must fail validation."""
        data = self._valid_data("-usr")
        serializer = TenantRegistrationSerializer(data=data)
        serializer.is_valid()
        serializer.save()
        # Same username, different slug
        data2 = self._valid_data("-usr")
        data2["slug"] = "different-slug"
        serializer2 = TenantRegistrationSerializer(data=data2)
        self.assertFalse(serializer2.is_valid())
        self.assertIn("username", serializer2.errors)

    def test_duplicate_email_is_rejected(self):
        """Registering with an existing email (case-insensitive) must fail validation."""
        data = self._valid_data("-mail")
        serializer = TenantRegistrationSerializer(data=data)
        serializer.is_valid()
        serializer.save()

        data2 = self._valid_data("-mail2")
        data2["email"] = data["email"].upper()
        serializer2 = TenantRegistrationSerializer(data=data2)
        self.assertFalse(serializer2.is_valid())
        self.assertIn("email", serializer2.errors)

    def test_short_password_is_rejected(self):
        """Password shorter than 8 characters must fail."""
        data = self._valid_data("-short")
        data["password"] = "123"
        serializer = TenantRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_invalid_email_is_rejected(self):
        """Malformed email must fail validation."""
        data = self._valid_data("-email")
        data["email"] = "not-an-email"
        serializer = TenantRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


# ─────────────────────────────────────────────
# Auth API Endpoint Tests
# ─────────────────────────────────────────────

class AuthAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="API Test Org", subdomain="api-test-org")
        self.user = TenantUser.objects.create_user(
            username="apiuser",
            email="api@test.com",
            password="testpass123",
            tenant=self.tenant,
            role="owner",
        )

    def test_login_with_valid_credentials(self):
        """POST /api/v1/auth/login/ returns 200 with tokens."""
        response = self.client.post("/api/v1/auth/login/", {
            "username": "apiuser",
            "password": "testpass123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password(self):
        """POST /api/v1/auth/login/ returns 401 for wrong password."""
        response = self.client.post("/api/v1/auth/login/", {
            "username": "apiuser",
            "password": "wrongpassword",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_email_uses_password_matched_account(self):
        """When multiple users share an email, login by email should match the correct password owner."""
        TenantUser.objects.create_user(
            username="apiuser2",
            email=self.user.email,
            password="otherpass123",
            tenant=self.tenant,
            role="member",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": self.user.email, "password": "testpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "apiuser")

    def test_login_with_email_field_works(self):
        """Login should work using the email field instead of username."""
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "testpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "apiuser")

    def test_login_with_email_conflict_when_multiple_password_matches(self):
        """If duplicate email accounts share the same password, API should ask for username."""
        TenantUser.objects.create_user(
            username="apiuser3",
            email=self.user.email,
            password="testpass123",
            tenant=self.tenant,
            role="member",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": self.user.email, "password": "testpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_register_new_tenant(self):
        """POST /api/v1/auth/register/ creates tenant and returns 201."""
        response = self.client.post("/api/v1/auth/register/", {
            "company_name": "New Corp",
            "slug": "new-corp",
            "username": "newcorpuser",
            "email": "newcorp@example.com",
            "password": "securepass123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)

    def test_protected_endpoint_requires_auth(self):
        """Accessing a protected endpoint without token returns 401."""
        response = self.client.get("/api/v1/documents/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_valid_token(self):
        """Accessing documents list with valid JWT returns 200."""
        login = self.client.post("/api/v1/auth/login/", {
            "username": "apiuser",
            "password": "testpass123",
        }, format="json")
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/documents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────
# QueryLog Model Tests
# ─────────────────────────────────────────────

class QueryLogModelTest(TestCase):

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Log Org", subdomain="log-org")

    def test_create_query_log(self):
        """QueryLog is created with correct fields."""
        log = QueryLog.objects.create(
            tenant=self.tenant,
            query="What is the refund policy?",
            answer="You can request a refund within 30 days.",
            response_time=1.23,
            chunks_used=3,
        )
        self.assertEqual(log.query, "What is the refund policy?")
        self.assertEqual(log.chunks_used, 3)
        self.assertAlmostEqual(log.response_time, 1.23)

    def test_query_log_ordering(self):
        """QueryLogs are ordered by most recent first."""
        QueryLog.objects.create(tenant=self.tenant, query="Q1", response_time=0.5)
        QueryLog.objects.create(tenant=self.tenant, query="Q2", response_time=0.6)
        logs = QueryLog.objects.filter(tenant=self.tenant)
        self.assertEqual(logs[0].query, "Q2")

    def test_query_log_tenant_isolation(self):
        """QueryLogs from one tenant are not visible to another."""
        other_tenant = Tenant.objects.create(name="Other Org", subdomain="other-org")
        QueryLog.objects.create(tenant=self.tenant, query="Secret Q", response_time=1.0)
        QueryLog.objects.create(tenant=other_tenant, query="Other Q", response_time=1.0)
        self.assertEqual(QueryLog.objects.filter(tenant=self.tenant).count(), 1)
        self.assertEqual(QueryLog.objects.filter(tenant=other_tenant).count(), 1)
