from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from .audit_helpers import ensure_demo_users, test_login_route, expected_dashboard_for_role

User = get_user_model()


class Command(BaseCommand):
    help = "Exibe acessos rápidos de demonstração do Educas (URLs e credenciais)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Verificando contas de demonstração..."))
        demo_users, demo_passwords = ensure_demo_users()

        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
        self.stdout.write("\nURL PRINCIPAL:")
        self.stdout.write(f"- {base_url}/")
        self.stdout.write("\nURL ADMIN:")
        self.stdout.write(f"- {base_url}/admin/")
        self.stdout.write("\nCREDS DE DEMONSTRAÇÃO:")

        for role_key, user in demo_users.items():
            password = demo_passwords.get(role_key)
            if not password:
                password_display = "(senha não disponível em produção)"
            else:
                password_display = password
            self.stdout.write(f"- {role_key.title()}: {user.email} / {password_display}")

        self.stdout.write("\nTESTE DE LOGIN AUTOMÁTICO:")
        for role_key, user in demo_users.items():
            password = demo_passwords.get(role_key)
            if not password:
                self.stdout.write(self.style.WARNING(f"Senha não disponível para {role_key}. Ignorando teste."))
                continue
            result = test_login_route(user, password)
            expected_path = expected_dashboard_for_role(user.role)
            success = result["logged_in"] and result["final_path"] == expected_path
            status = "OK" if success else "FALHA"
            self.stdout.write(f"- {role_key.title()}: {status} (destino esperado: {expected_path}, final: {result['final_path']})")

        self.stdout.write("\nDICA: use python manage.py audit_users para ver o relatório de URLs, permissões e usuários.")
