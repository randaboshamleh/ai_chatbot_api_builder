from apps.tenants.models import TenantUser

users = TenantUser.objects.all()
print("=== All Registered Users ===")
print(f"Total: {users.count()}")
print()
for u in users:
    tenant_name = u.tenant.name if u.tenant else "None"
    print(f"Username: {u.username}")
    print(f"Email: {u.email}")
    print(f"Tenant: {tenant_name}")
    print(f"Role: {u.role}")
    print("---")
