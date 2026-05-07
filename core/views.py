from django.shortcuts import render

from .models import Disciplina, EventoAcademico, Nota, PostFeed, Turma, UsuarioSistema


def static_page(template_name):
    def view(request):
        return render(request, f"core/{template_name}")

    return view


home = static_page("index.html")
login = static_page("login.html")
cadastro = static_page("cadastro.html")
feed = static_page("feed.html")
perfil = static_page("profile.html")
turmas = static_page("turmas.html")
notas = static_page("notas.html")
calendario = static_page("calendario.html")


def administrador(request):
    context = {
        "total_usuarios": UsuarioSistema.objects.count(),
        "total_turmas": Turma.objects.count(),
        "total_disciplinas": Disciplina.objects.count(),
        "total_eventos": EventoAcademico.objects.count(),
        "usuarios": UsuarioSistema.objects.all()[:6],
        "turmas": Turma.objects.prefetch_related("disciplinas")[:4],
        "eventos": EventoAcademico.objects.all()[:6],
        "notas": Nota.objects.select_related("aluno")[:6],
        "posts": PostFeed.objects.all()[:5],
    }
    return render(request, "core/administrador.html", context)
