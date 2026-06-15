from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("index.html", views.home, name="home_html"),
    path("login.html", views.EducasLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cadastro.html", views.cadastro, name="cadastro"),
    path("professor.html", views.professor_dashboard, name="professor"),
    path("professor/atividades.html", views.assignment_list, name="assignment_list"),
    path("professor/atividades/criar.html", views.assignment_create, name="assignment_create"),
    path("professor/atividades/<int:assignment_id>/editar.html", views.assignment_edit, name="assignment_edit"),
    path("professor/atividades/<int:assignment_id>/detalhe.html", views.assignment_detail, name="assignment_detail"),
    path("aluno.html", views.aluno_dashboard, name="aluno"),
    path("notificacoes.html", views.notifications, name="notifications"),
    path("atividades.html", views.student_assignment_list, name="student_assignments"),
    path("atividades/<int:assignment_id>/detalhe.html", views.assignment_detail, name="student_assignment_detail"),
    path("feed.html", views.feed, name="feed"),
    path("feed/review-ai/", views.feed_review_ai, name="feed_review_ai"),
    path("feed/reactions/", views.feed_react, name="feed_react"),
    path("feed/comments/", views.feed_comment, name="feed_comment"),
    path("feed/comments/delete/", views.feed_delete_comment, name="feed_delete_comment"),
    path("profile.html", views.perfil, name="perfil"),
    path("turmas.html", views.turmas, name="turmas"),
    path("turmas/<int:classroom_id>/cronograma.html", views.classroom_schedule, name="classroom_schedule"),
    path("aulas.html", views.aulas, name="aulas"),
    path("aulas/<int:lesson_id>/editar.html", views.editar_aula, name="editar_aula"),
    path("aulas/<int:lesson_id>/frequencia.html", views.lesson_attendance, name="lesson_attendance"),
    path("notas.html", views.notas, name="notas"),
    path("attendance.html", views.attendance, name="attendance"),
    path("grades_batch.html", views.grades_batch, name="grades_batch"),
    path("calendario.html", views.calendario, name="calendario"),
    path("administrador.html", views.administrador, name="administrador_html"),
    path("administrador/", views.administrador, name="administrador"),
]
