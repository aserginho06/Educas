from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils.crypto import get_random_string

User = get_user_model()

DEMO_USERS = {
    "admin": {
        "email": "admin@educas.local",
        "first_name": "Admin",
        "last_name": "Educas",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
    "teacher": {
        "email": "prof.roberto@educas.local",
        "first_name": "Roberto",
        "last_name": "Santos",
        "role": User.Role.TEACHER,
    },
    "student": {
        "email": "aluno.thiallisson@educas.local",
        "first_name": "Thiallisson",
        "last_name": "Oliveira",
        "role": User.Role.STUDENT,
    },
}

URLS_TO_CHECK = [
    "/",
    "/login/",
    "/login.html",
    "/admin/",
    "/professor/",
    "/professor.html",
    "/aluno/",
    "/aluno.html",
    "/feed/",
    "/feed.html",
    "/aulas/",
    "/aulas.html",
    "/attendance/",
    "/attendance.html",
    "/notas/",
    "/notas.html",
    "/turmas/",
    "/turmas.html",
    "/calendario/",
    "/calendario.html",
    "/grades_batch/",
    "/grades_batch.html",
    "/administrador/",
    "/administrador.html",
]

LOGIN_ROUTE = "/login.html"


def generate_temporary_password(length: int = 12) -> str:
    return get_random_string(length)


def ensure_demo_users():
    account_map = {}
    passwords = {}

    for account_key, account_data in DEMO_USERS.items():
        defaults = {
            "first_name": account_data["first_name"],
            "last_name": account_data["last_name"],
            "role": account_data["role"],
            "is_staff": account_data.get("is_staff", False),
            "is_superuser": account_data.get("is_superuser", False),
        }
        user, created = User.objects.get_or_create(email=account_data["email"], defaults=defaults)

        if created:
            user.set_password(generate_temporary_password())
            user.save()

        if settings.DEBUG:
            password = generate_temporary_password()
            user.set_password(password)
            user.save()
            passwords[account_key] = password
        else:
            passwords[account_key] = None

        account_map[account_key] = user

    return account_map, passwords


def format_permission(permission_labels):
    if not permission_labels:
        return "Nenhum acesso"
    if permission_labels == ["public"]:
        return "Public"
    return "+".join(permission_labels).capitalize()


def summarize_permissions(anon_status, role_access):
    if anon_status == 200:
        return "Public"
    allowed = [role for role, status in role_access.items() if status == 200]
    if allowed:
        return f"Authenticated: {', '.join(role.title() for role in allowed)}"
    if anon_status in {302, 301}:
        return "Authentication required"
    if anon_status == 403:
        return "Access denied"
    if anon_status == 404:
        return "Not found"
    return "Unknown"


def test_urls(urls=None, users=None):
    client = Client()
    urls = urls or URLS_TO_CHECK
    results = []

    for url in urls:
        response = client.get(url, follow=False)
        status = response.status_code
        redirect = response.get("Location", "")
        access_status = {}

        if users:
            for role, user in users.items():
                client.logout()
                client.force_login(user)
                role_response = client.get(url, follow=False)
                access_status[role] = role_response.status_code

        permission = summarize_permissions(status, access_status)
        results.append(
            {
                "url": url,
                "status": status,
                "redirect": redirect,
                "permission": permission,
                "access_status": access_status,
            }
        )

    return results


def test_login_route(user, password):
    client = Client()
    response = client.post(LOGIN_ROUTE, {"username": user.email, "password": password}, follow=True)
    logged_in = False
    if getattr(response, "context", None):
        user_obj = response.context.get("user")
        logged_in = bool(user_obj and user_obj.is_authenticated)

    final_path = response.request.get("PATH_INFO") if hasattr(response, "request") else ""
    return {
        "status": response.status_code,
        "logged_in": logged_in,
        "final_path": final_path,
        "redirect_chain": response.redirect_chain,
    }


def expected_dashboard_for_role(role):
    if role == User.Role.ADMIN:
        return "/administrador/"
    if role == User.Role.TEACHER:
        return "/professor.html"
    return "/aluno/"
