from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from .audit_helpers import ensure_demo_users, test_login_route, test_urls, expected_dashboard_for_role

User = get_user_model()


class Command(BaseCommand):
    help = "Audita usuários, rotas e acesso de demonstração no Educas."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando auditoria de usuários e URLs..."))

        demo_users, demo_passwords = ensure_demo_users()
        self.stdout.write(self.style.SUCCESS("Contas demo verificadas."))

        users = User.objects.order_by("role", "first_name", "email")
        self.stdout.write("\nUSUÁRIOS CADASTRADOS:")
        self.stdout.write("ID | Nome | Email | Perfil")
        self.stdout.write("---|------|-------|--------")
        for user in users:
            name = user.full_name or "(sem nome)"
            self.stdout.write(f"{user.id} | {name} | {user.email} | {user.get_role_display()}")

        role_counts = {
            "Administradores": User.objects.filter(role=User.Role.ADMIN).count(),
            "Professores": User.objects.filter(role=User.Role.TEACHER).count(),
            "Alunos": User.objects.filter(role=User.Role.STUDENT).count(),
        }
        self.stdout.write("\nCONTA DE PERFIS:")
        for label, count in role_counts.items():
            self.stdout.write(f"- {label}: {count}")

        self.stdout.write("\nDIAGNÓSTICO DE URLS:")
        url_results = test_urls(users=demo_users)
        self.stdout.write("URL | Status | Redirecionamento | Permissão")
        self.stdout.write("---|--------|------------------|-----------")
        for result in url_results:
            redirect = result["redirect"] or "-"
            self.stdout.write(f"{result['url']} | {result['status']} | {redirect} | {result['permission']}")

        self.stdout.write("\nTESTE DE LOGIN DE DEMONSTRAÇÃO:")
        self.stdout.write("Usuário | Login | Redirecionamento esperado | Caminho final | Sucesso")
        for role_key, user in demo_users.items():
            password = demo_passwords.get(role_key)
            if not password:
                self.stdout.write(self.style.WARNING(f"Senha temporária não disponível para {role_key}. Ignorando teste de login."))
                continue

            result = test_login_route(user, password)
            expected_path = expected_dashboard_for_role(user.role)
            success = result["logged_in"] and result["final_path"] == expected_path
            status = "OK" if success else "FALHA"
            self.stdout.write(
                f"{role_key.title()} | {user.email}:{password} | {expected_path} | {result['final_path']} | {status}"
            )

        self.stdout.write("\nRELATÓRIO FINAL:")
        self.stdout.write("- Serviços auditados: URLs principais e login de demonstração.")
        self.stdout.write("- Usuários exibidos e contas demo garantidas em DEBUG.")
        self.stdout.write("- Caso precise de acesso rápido, execute: python manage.py demo_access")
