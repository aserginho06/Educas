from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Disciplina, EventoAcademico, Nota, PostFeed, Turma, UsuarioSistema


class Command(BaseCommand):
    help = "Cria dados iniciais para demonstrar o painel administrativo Educas."

    def handle(self, *args, **options):
        user_model = get_user_model()
        admin_user, created = user_model.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@educas.local", "is_staff": True, "is_superuser": True},
        )

        if created:
            admin_user.set_password("admin123")
            admin_user.save()

        turma, _ = Turma.objects.get_or_create(
            nome="3o Ano B",
            defaults={"ano_letivo": 2026, "periodo": "Manha"},
        )
        UsuarioSistema.objects.get_or_create(
            email="thiallisson@educas.com",
            defaults={
                "nome": "Thiallisson Oliveira",
                "matricula": "202500123",
                "perfil": UsuarioSistema.Perfil.ALUNO,
                "turma": turma.nome,
                "telefone": "(86) 99999-9999",
            },
        )
        UsuarioSistema.objects.get_or_create(
            email="roberto@educas.com",
            defaults={
                "nome": "Roberto Santos",
                "matricula": "PROF001",
                "perfil": UsuarioSistema.Perfil.PROFESSOR,
                "turma": turma.nome,
            },
        )
        Disciplina.objects.get_or_create(
            nome="Matematica",
            turma=turma,
            defaults={"professor": "Prof. Roberto Santos", "horario": "Seg e Qua - 08:00"},
        )
        Disciplina.objects.get_or_create(
            nome="Historia",
            turma=turma,
            defaults={"professor": "Profa. Amanda Lima", "horario": "Ter e Qui - 09:40"},
        )
        EventoAcademico.objects.get_or_create(
            titulo="Simulado de Matematica",
            data=date(2026, 5, 8),
            defaults={"tipo": EventoAcademico.Tipo.AVALIACAO, "disciplina": "Matematica"},
        )
        EventoAcademico.objects.get_or_create(
            titulo="Entrega de Historia",
            data=date(2026, 5, 15),
            defaults={"tipo": EventoAcademico.Tipo.ENTREGA, "disciplina": "Historia"},
        )
        aluno = UsuarioSistema.objects.get(email="thiallisson@educas.com")
        Nota.objects.get_or_create(
            aluno=aluno,
            disciplina="Matematica",
            avaliacao="AV1",
            defaults={"valor": 8.5},
        )
        PostFeed.objects.get_or_create(
            autor="Educas AI",
            categoria="Sugestao",
            defaults={"conteudo": "Resumo visual e quiz rapido para revisar Revolucao Industrial."},
        )

        self.stdout.write(self.style.SUCCESS("Dados iniciais criados. Login do Django Admin: admin / admin123"))
