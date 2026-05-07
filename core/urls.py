from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("index.html", views.home, name="home_html"),
    path("login.html", views.login, name="login"),
    path("cadastro.html", views.cadastro, name="cadastro"),
    path("feed.html", views.feed, name="feed"),
    path("profile.html", views.perfil, name="perfil"),
    path("turmas.html", views.turmas, name="turmas"),
    path("notas.html", views.notas, name="notas"),
    path("calendario.html", views.calendario, name="calendario"),
    path("administrador.html", views.administrador, name="administrador_html"),
    path("administrador/", views.administrador, name="administrador"),
]
