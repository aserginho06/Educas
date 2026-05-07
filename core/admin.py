from django.contrib import admin

from .models import Disciplina, EventoAcademico, Nota, PostFeed, Turma, UsuarioSistema


@admin.register(UsuarioSistema)
class UsuarioSistemaAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "perfil", "turma", "ativo")
    list_filter = ("perfil", "ativo")
    search_fields = ("nome", "email", "matricula", "turma")


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ano_letivo", "periodo", "ativa")
    list_filter = ("ano_letivo", "ativa")
    search_fields = ("nome",)


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("nome", "turma", "professor", "horario")
    list_filter = ("turma",)
    search_fields = ("nome", "professor")


@admin.register(EventoAcademico)
class EventoAcademicoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "data", "tipo", "disciplina")
    list_filter = ("tipo", "data")
    search_fields = ("titulo", "disciplina")


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "disciplina", "avaliacao", "valor", "criado_em")
    list_filter = ("disciplina",)
    search_fields = ("aluno__nome", "disciplina", "avaliacao")


@admin.register(PostFeed)
class PostFeedAdmin(admin.ModelAdmin):
    list_display = ("autor", "categoria", "publicado", "criado_em")
    list_filter = ("categoria", "publicado")
    search_fields = ("autor", "conteudo")
