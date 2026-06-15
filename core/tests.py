import os
from datetime import time, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from academics.models import AcademicEvent, AcademicYear, Assessment, Attendance, AttendanceRecord, Classroom, ClassroomSubject, Enrollment, Grade, GradeEntry, GradeLevel, Lesson, Subject, WeeklySchedule
from academics.services import student_attendance_summary
from assignments.models import Assignment, Submission
from common.ai_content import generate_json, get_ai_configuration
from core.management.commands.seed_institutional import Command as SeedInstitutionalCommand
from engagement.models import Comment, Post, PostReaction


class AcademicFactoryMixin:
    @classmethod
    def get_academic_year(cls, year=None):
        target_year = year or timezone.now().year
        academic_year, _ = AcademicYear.objects.get_or_create(
            year=target_year,
            defaults={"name": str(target_year), "is_active": True},
        )
        return academic_year

    @classmethod
    def get_grade_level(cls, code="2EM"):
        defaults_map = {
            "2EM": {
                "name": "2o Ano EM",
                "stage": GradeLevel.EducationStage.HIGH_SCHOOL,
                "sequence": 11,
            },
            "3EM": {
                "name": "3o Ano EM",
                "stage": GradeLevel.EducationStage.HIGH_SCHOOL,
                "sequence": 12,
            },
        }
        defaults = defaults_map.get(
            code,
            {
                "name": code,
                "stage": GradeLevel.EducationStage.HIGH_SCHOOL,
                "sequence": 99,
            },
        )
        grade_level, _ = GradeLevel.objects.get_or_create(code=code, defaults=defaults)
        return grade_level


class CoreFlowTests(AcademicFactoryMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="boss@educas.com",
            password="admin123",
            first_name="Boss",
            last_name="Admin",
        )
        cls.teacher = User.objects.create_user(
            email="teacher@educas.com",
            password="12345678",
            first_name="Paula",
            role=User.Role.TEACHER,
        )
        cls.student = User.objects.create_user(
            email="student@educas.com",
            password="12345678",
            first_name="Nina",
            role=User.Role.STUDENT,
        )
        cls.other_student = User.objects.create_user(
            email="otherstudent@educas.com",
            password="12345678",
            first_name="Leo",
            role=User.Role.STUDENT,
        )
        cls.academic_year = cls.get_academic_year()
        cls.grade_level = cls.get_grade_level()
        cls.subject = Subject.objects.create(code="MAT101", name="Matematica")
        cls.classroom = Classroom.objects.create(
            name="2EM-A",
            school_year=cls.academic_year.year,
            academic_year=cls.academic_year,
            grade_level=cls.grade_level,
            shift=Classroom.Shift.MORNING,
            section="A",
            homeroom_teacher=cls.teacher,
            created_by=cls.admin,
        )
        ClassroomSubject.objects.create(classroom=cls.classroom, subject=cls.subject, teacher=cls.teacher)
        Enrollment.objects.create(student=cls.student, classroom=cls.classroom, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(student=cls.other_student, classroom=cls.classroom, status=Enrollment.Status.APPROVED)
        cls.post = Post.objects.create(
            classroom=cls.classroom,
            author=cls.teacher,
            subject=cls.subject,
            title="Aviso",
            content="Conteudo real",
        )
        AcademicEvent.objects.create(
            classroom=cls.classroom,
            subject=cls.subject,
            created_by=cls.teacher,
            title="Prova 1",
            starts_at=timezone.now() + timedelta(days=2),
        )
        cls.assignment = Assignment.objects.create(
            classroom=cls.classroom,
            subject=cls.subject,
            author=cls.teacher,
            title="Lista Avaliativa",
            description="Resolver e enviar.",
            due_at=timezone.now() + timedelta(days=1),
        )

    def test_default_admin_is_created_after_migrations(self):
        self.assertTrue(User.objects.filter(email="admin@educas.com", role=User.Role.ADMIN).exists())

    def test_seeded_academic_year_is_reused_without_duplicate(self):
        academic_year = self.get_academic_year(self.academic_year.year)
        self.assertEqual(academic_year.pk, self.academic_year.pk)
        self.assertEqual(AcademicYear.objects.filter(year=self.academic_year.year).count(), 1)

    def test_admin_login_redirects_to_admin_dashboard(self):
        self.client.login(email="boss@educas.com", password="admin123")
        response = self.client.get(reverse("core:login"))
        self.assertRedirects(response, reverse("core:administrador"))

    def test_student_login_redirects_to_feed(self):
        self.client.login(email="student@educas.com", password="12345678")
        response = self.client.get(reverse("core:login"))
        self.assertRedirects(response, reverse("core:aluno"))

    def test_teacher_login_redirects_to_teacher_dashboard(self):
        self.client.login(email="teacher@educas.com", password="12345678")
        response = self.client.get(reverse("core:login"))
        self.assertRedirects(response, reverse("core:professor"))

    def test_turmas_page_shows_class_summary_cards(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:turmas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver Cronograma")
        self.assertContains(response, "2EM-A")
        self.assertContains(response, "alunos")
        self.assertContains(response, "disciplinas")

    def test_classroom_schedule_page_renders_weekly_timetable(self):
        WeeklySchedule.objects.create(
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            entry_type=WeeklySchedule.EntryType.CLASS,
            weekday=WeeklySchedule.Weekday.MONDAY,
            starts_at=time(7, 0),
            ends_at=time(7, 45),
        )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:classroom_schedule", args=[self.classroom.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Segunda")
        self.assertContains(response, "Matematica")

    def test_student_cannot_create_classroom(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("core:turmas"),
            {
                "action": "create_classroom",
                "create-name": "Turma Pirata",
                "create-academic_year": self.academic_year.pk,
                "create-grade_level": self.grade_level.pk,
                "create-shift": Classroom.Shift.AFTERNOON,
                "create-section": "B",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Classroom.objects.filter(name="Turma Pirata").exists())

    def test_teacher_cannot_create_classroom(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:turmas"),
            {
                "action": "create_classroom",
                "create-name": "Turma Invalida",
                "create-academic_year": self.academic_year.pk,
                "create-grade_level": self.grade_level.pk,
                "create-shift": Classroom.Shift.EVENING,
                "create-section": "C",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Classroom.objects.filter(name="Turma Invalida").exists())

    def test_teacher_can_create_post_for_linked_subject(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:feed"),
            {
                "action": "create_post",
                "post-classroom": self.classroom.pk,
                "post-subject": self.subject.pk,
                "post-post_type": "material",
                "post-title": "Lista 2",
                "post-content": "Arquivos e orientacoes",
                "post-is_pinned": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Post.objects.filter(title="Lista 2", author=self.teacher).exists())

    def test_teacher_can_create_lesson_for_linked_classroom_and_subject(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:aulas"),
            {
                "lesson-classroom": self.classroom.pk,
                "lesson-subject": self.subject.pk,
                "lesson-date": timezone.localdate().isoformat(),
                "lesson-quantidade_aulas": 2,
                "lesson-conteudo": "Revisao de equacoes.",
                "lesson-atividade": "Lista de exercicios de algebra.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Lesson.objects.filter(professor=self.teacher, classroom=self.classroom, subject=self.subject).exists())
        lesson = Lesson.objects.get(professor=self.teacher, classroom=self.classroom, subject=self.subject)
        self.assertEqual(lesson.quantidade_aulas, 2)
        self.assertEqual(lesson.conteudo, "Revisao de equacoes.")

    def test_teacher_can_edit_lesson(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=1,
            conteudo="Conteudo inicial.",
            atividade="Atividade inicial.",
        )
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:editar_aula", args=[lesson.pk]),
            {
                "lesson-classroom": self.classroom.pk,
                "lesson-subject": self.subject.pk,
                "lesson-date": timezone.localdate().isoformat(),
                "lesson-quantidade_aulas": 3,
                "lesson-conteudo": "Conteudo atualizado.",
                "lesson-atividade": "Atividade atualizada.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        lesson.refresh_from_db()
        self.assertEqual(lesson.quantidade_aulas, 3)
        self.assertEqual(lesson.conteudo, "Conteudo atualizado.")

    def test_teacher_can_filter_lessons_by_classroom_and_date(self):
        other_subject = Subject.objects.create(code="POR102", name="Portugues")
        Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=1,
            conteudo="Matematica.",
            atividade="Exercicio 1.",
        )
        Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=other_subject,
            date=timezone.localdate() + timedelta(days=1),
            quantidade_aulas=1,
            conteudo="Portugues.",
            atividade="Exercicio 2.",
        )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:aulas") + f"?date={timezone.localdate().isoformat()}")
        self.assertContains(response, "Matematica.")
        self.assertNotContains(response, "Portugues.")

    def test_teacher_cannot_edit_another_teachers_lesson(self):
        other_teacher = User.objects.create_user(
            email="teacher2@educas.com",
            password="12345678",
            first_name="Rafael",
            role=User.Role.TEACHER,
        )
        lesson = Lesson.objects.create(
            professor=other_teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=1,
            conteudo="Outra aula.",
            atividade="Outra atividade.",
        )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:editar_aula", args=[lesson.pk]))
        self.assertEqual(response.status_code, 404)

    def test_lesson_persists_in_database(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=4,
            conteudo="Atividade de geometria.",
            atividade="Exercicios de superficie.",
        )
        self.assertEqual(Lesson.objects.count(), 1)
        self.assertEqual(lesson.professor, self.teacher)
        self.assertEqual(lesson.classroom, self.classroom)
        self.assertEqual(lesson.subject, self.subject)

    def test_sync_post_creation_redirects_and_post_is_visible_in_feed(self):
        self.client.force_login(self.teacher)
        create_response = self.client.post(
            reverse("core:feed"),
            {
                "action": "create_post",
                "post-classroom": self.classroom.pk,
                "post-subject": self.subject.pk,
                "post-post_type": "announcement",
                "post-title": "Post sincronizado",
                "post-content": "Tem que aparecer no mural.",
            },
            follow=True,
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(Post.objects.filter(title="Post sincronizado", author=self.teacher).exists())
        feed_response = self.client.get(reverse("core:feed"))
        self.assertContains(feed_response, "Post sincronizado")

    def test_teacher_can_create_post_asynchronously_and_receive_json(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:feed"),
            {
                "action": "create_post",
                "post-classroom": self.classroom.pk,
                "post-subject": self.subject.pk,
                "post-post_type": "announcement",
                "post-title": "Post imediato",
                "post-content": "Sai no topo sem recarregar.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["post"]["title"], "Post imediato")
        self.assertTrue(Post.objects.filter(title="Post imediato", author=self.teacher).exists())
        feed_response = self.client.get(reverse("core:feed"))
        self.assertContains(feed_response, "Post imediato")

    def test_teacher_dashboard_requires_teacher_role(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:professor"))
        self.assertEqual(response.status_code, 403)

    def test_student_can_comment_and_like_post(self):
        self.client.force_login(self.student)
        comment_response = self.client.post(
            reverse("core:feed_comment"),
            {
                "post_id": self.post.pk,
                "comment-content": "Entendi o recado",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        like_response = self.client.post(
            reverse("core:feed_react"),
            {
                "post_id": self.post.pk,
                "reaction_type": "like",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(comment_response.status_code, 201)
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(Comment.objects.filter(post=self.post, author=self.student).exists())
        self.assertTrue(PostReaction.objects.filter(post=self.post, user=self.student, reaction_type="like").exists())
        self.assertEqual(comment_response.json()["comment"]["author"], self.student.full_name)
        self.assertEqual(like_response.json()["current_user_reaction"], "like")

    def test_multiple_users_can_like_same_post_without_duplicates(self):
        first_client = self.client
        second_client = Client()
        first_client.force_login(self.student)
        second_client.force_login(self.other_student)

        first_response = first_client.post(
            reverse("core:feed_react"),
            {"post_id": self.post.pk, "reaction_type": "like"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        second_response = second_client.post(
            reverse("core:feed_react"),
            {"post_id": self.post.pk, "reaction_type": "like"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(PostReaction.objects.filter(post=self.post, reaction_type="like").count(), 2)
        self.assertEqual(first_response.json()["current_user_reaction"], "like")
        self.assertEqual(second_response.json()["current_user_reaction"], "like")

    def test_reaction_toggle_removes_same_reaction(self):
        self.client.force_login(self.student)
        self.client.post(
            reverse("core:feed_react"),
            {"post_id": self.post.pk, "reaction_type": "like"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        second_response = self.client.post(
            reverse("core:feed_react"),
            {"post_id": self.post.pk, "reaction_type": "like"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(PostReaction.objects.filter(post=self.post, user=self.student).exists())
        self.assertIsNone(second_response.json()["current_user_reaction"])

    def test_multiple_users_can_comment_and_update_comment_count(self):
        first_client = self.client
        second_client = Client()
        first_client.force_login(self.student)
        second_client.force_login(self.other_student)

        first_comment_response = first_client.post(
            reverse("core:feed_comment"),
            {"post_id": self.post.pk, "comment-content": "Primeiro comentario"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        second_comment_response = second_client.post(
            reverse("core:feed_comment"),
            {"post_id": self.post.pk, "comment-content": "Segundo comentario"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(first_comment_response.status_code, 201)
        self.assertEqual(second_comment_response.status_code, 201)
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 2)
        self.assertEqual(second_comment_response.json()["comment_count"], 2)
        self.assertEqual(first_comment_response.json()["comment"]["author"], self.student.full_name)
        self.assertEqual(second_comment_response.json()["comment"]["author"], self.other_student.full_name)

    def test_can_comment_on_new_post_and_persist_in_database(self):
        new_post = Post.objects.create(
            classroom=self.classroom,
            author=self.teacher,
            subject=self.subject,
            title="Novo aviso",
            content="Conteudo recente",
        )
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("core:feed_comment"),
            {"post_id": new_post.pk, "comment-content": "Comentario no post novo"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.filter(post=new_post).count(), 1)
        self.assertEqual(response.json()["comment_count"], 1)
        self.assertEqual(response.json()["comment"]["content"], "Comentario no post novo")
        self.assertTrue(Comment.objects.filter(post=new_post, author=self.student).exists())

    def test_feed_lists_newest_posts_first(self):
        newer_post = Post.objects.create(
            classroom=self.classroom,
            author=self.teacher,
            subject=self.subject,
            title="Post novo",
            content="Mais recente",
        )
        older_post = Post.objects.create(
            classroom=self.classroom,
            author=self.teacher,
            subject=self.subject,
            title="Post antigo",
            content="Mais antigo",
        )
        Post.objects.filter(pk=older_post.pk).update(created_at=timezone.now() - timedelta(days=2))
        Post.objects.filter(pk=newer_post.pk).update(created_at=timezone.now())
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:feed"))
        content = response.content.decode("utf-8")
        self.assertLess(content.find("Post novo"), content.find("Post antigo"))

    def test_student_can_delete_own_comment_without_refresh(self):
        self.client.force_login(self.student)
        comment = Comment.objects.create(post=self.post, author=self.student, content="Apagar depois")
        response = self.client.post(
            reverse("core:feed_delete_comment"),
            {"comment_id": comment.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
        self.assertIn("comment_count", response.json())

    def test_teacher_can_save_attendance_for_lesson(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=3,
            conteudo="Revisao de trigonometria.",
            atividade="Lista 05.",
        )
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:lesson_attendance", args=[lesson.pk]),
            {
                f"absences_{self.student.id}": "2",
                f"absences_{self.other_student.id}": "1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.filter(lesson=lesson).count(), 2)
        self.assertEqual(AttendanceRecord.objects.get(lesson=lesson, student=self.student).absences, 2)
        self.assertEqual(AttendanceRecord.objects.get(lesson=lesson, student=self.other_student).absences, 1)

    def test_teacher_can_edit_attendance_for_lesson(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=3,
            conteudo="Revisao de trigonometria.",
            atividade="Lista 05.",
        )
        AttendanceRecord.objects.create(lesson=lesson, student=self.student, absences=2)
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:lesson_attendance", args=[lesson.pk]),
            {
                f"absences_{self.student.id}": "0",
                f"absences_{self.other_student.id}": "1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.get(lesson=lesson, student=self.student).absences, 0)

    def test_absences_accumulate_correctly_across_lessons(self):
        lesson_one = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=2,
            conteudo="Conteudo 1.",
            atividade="Atividade 1.",
        )
        lesson_two = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate() + timedelta(days=1),
            quantidade_aulas=1,
            conteudo="Conteudo 2.",
            atividade="Atividade 2.",
        )
        AttendanceRecord.objects.create(lesson=lesson_one, student=self.student, absences=2)
        AttendanceRecord.objects.create(lesson=lesson_two, student=self.student, absences=1)
        summary = student_attendance_summary(self.student)
        self.assertEqual(summary["absences"], 3)
        self.assertEqual(summary["frequency"], 0.0)

    def test_teacher_cannot_access_another_teachers_lesson_attendance(self):
        other_teacher = User.objects.create_user(
            email="teacher2@educas.com",
            password="12345678",
            first_name="Rafael",
            role=User.Role.TEACHER,
        )
        lesson = Lesson.objects.create(
            professor=other_teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=2,
            conteudo="Outra aula.",
            atividade="Outra atividade.",
        )
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:lesson_attendance", args=[lesson.pk]))
        self.assertEqual(response.status_code, 404)

    def test_student_views_attendance_summary(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=2,
            conteudo="Geometria.",
            atividade="Exercicio.",
        )
        AttendanceRecord.objects.create(lesson=lesson, student=self.student, absences=1)
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:aluno"))
        content = response.content.decode()
        self.assertContains(response, "1 falta")
        self.assertTrue("50,0%" in content or "50.0%" in content)

    def test_attendance_record_persists_in_database(self):
        lesson = Lesson.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            date=timezone.localdate(),
            quantidade_aulas=3,
            conteudo="Geometria analitica.",
            atividade="Exercicio total.",
        )
        record = AttendanceRecord.objects.create(lesson=lesson, student=self.student, absences=2)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        self.assertEqual(record.lesson, lesson)
        self.assertEqual(record.student, self.student)
        self.assertEqual(record.absences, 2)

    def test_teacher_can_save_grades_in_batch(self):
        assessment = Assessment.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            assessment_type=Assessment.AssessmentType.P1,
            date=timezone.localdate(),
            description="Prova mensal",
            quantidade_aulas=2,
        )
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:grades_batch"),
            {
                "action": "save_grades",
                "assessment_id": assessment.pk,
                f"score_{self.student.id}": "8.5",
                f"score_{self.other_student.id}": "7.0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GradeEntry.objects.filter(assessment=assessment).count(), 2)
        self.assertTrue(GradeEntry.objects.filter(assessment=assessment, student=self.student).exists())

    def test_teacher_can_create_assessment(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:grades_batch"),
            {
                "action": "create_assessment",
                "assessment-classroom": self.classroom.pk,
                "assessment-subject": self.subject.pk,
                "assessment-assessment_type": Assessment.AssessmentType.P1,
                "assessment-date": timezone.localdate().isoformat(),
                "assessment-description": "Prova de Trigonometria",
                "assessment-quantidade_aulas": "2",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Assessment.objects.filter(classroom=self.classroom, subject=self.subject, assessment_type=Assessment.AssessmentType.P1).exists())

    def test_teacher_can_save_grade_entries_for_assessment(self):
        assessment = Assessment.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            assessment_type=Assessment.AssessmentType.P1,
            date=timezone.localdate(),
            description="Prova 1",
            quantidade_aulas=2,
        )
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:grades_batch"),
            {
                "action": "save_grades",
                "assessment_id": assessment.pk,
                f"score_{self.student.id}": "8.0",
                f"score_{self.other_student.id}": "7.5",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GradeEntry.objects.filter(assessment=assessment).count(), 2)
        self.assertEqual(GradeEntry.objects.get(assessment=assessment, student=self.student).score, 8.0)

    def test_assessment_grade_entry_is_unique_per_student(self):
        assessment = Assessment.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            assessment_type=Assessment.AssessmentType.P1,
            date=timezone.localdate(),
            description="Prova unica",
            quantidade_aulas=1,
        )
        GradeEntry.objects.create(assessment=assessment, student=self.student, score=6.5)
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("core:grades_batch"),
            {
                "action": "save_grades",
                "assessment_id": assessment.pk,
                f"score_{self.student.id}": "8.0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GradeEntry.objects.filter(assessment=assessment, student=self.student).count(), 1)
        self.assertEqual(float(GradeEntry.objects.get(assessment=assessment, student=self.student).score), 8.0)

    def test_student_grade_report_computes_status(self):
        assessment_p1 = Assessment.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            assessment_type=Assessment.AssessmentType.P1,
            date=timezone.localdate(),
            description="P1",
            quantidade_aulas=1,
        )
        assessment_rec1 = Assessment.objects.create(
            professor=self.teacher,
            classroom=self.classroom,
            subject=self.subject,
            assessment_type=Assessment.AssessmentType.REC1,
            date=timezone.localdate(),
            description="REC1",
            quantidade_aulas=1,
        )
        GradeEntry.objects.create(assessment=assessment_p1, student=self.student, score=6.0)
        GradeEntry.objects.create(assessment=assessment_rec1, student=self.student, score=8.0)
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:notas"))
        self.assertContains(response, "AP")
        self.assertContains(response, "8.0")

    def test_teacher_cannot_access_another_teachers_lesson_attendance(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("core:aluno"))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_see_admin_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:administrador"))
        self.assertEqual(response.status_code, 403)

    def test_calendar_shows_scoped_events(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:calendario"))
        self.assertContains(response, "Prova 1")

    def test_weekly_schedule_prevents_overlap(self):
        WeeklySchedule.objects.create(
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            weekday=WeeklySchedule.Weekday.MONDAY,
            starts_at=time(7, 0),
            ends_at=time(7, 50),
        )
        overlapping = WeeklySchedule(
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            weekday=WeeklySchedule.Weekday.MONDAY,
            starts_at=time(7, 30),
            ends_at=time(8, 10),
        )
        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_weekly_schedule_rejects_class_during_break(self):
        WeeklySchedule.objects.create(
            classroom=self.classroom,
            weekday=WeeklySchedule.Weekday.TUESDAY,
            starts_at=time(8, 40),
            ends_at=time(9, 0),
            entry_type=WeeklySchedule.EntryType.BREAK,
        )
        blocked = WeeklySchedule(
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            weekday=WeeklySchedule.Weekday.TUESDAY,
            starts_at=time(8, 45),
            ends_at=time(9, 30),
            entry_type=WeeklySchedule.EntryType.CLASS,
        )
        with self.assertRaises(ValidationError):
            blocked.full_clean()

    def test_weekly_schedule_rejects_teacher_conflict_between_classrooms(self):
        other_classroom = Classroom.objects.create(
            name="3EM-A",
            school_year=self.academic_year.year,
            academic_year=self.academic_year,
            grade_level=self.get_grade_level("3EM"),
            shift=Classroom.Shift.MORNING,
            section="A",
            homeroom_teacher=self.teacher,
            created_by=self.admin,
        )
        WeeklySchedule.objects.create(
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            weekday=WeeklySchedule.Weekday.WEDNESDAY,
            starts_at=time(7, 0),
            ends_at=time(7, 50),
            entry_type=WeeklySchedule.EntryType.CLASS,
        )
        conflicting = WeeklySchedule(
            classroom=other_classroom,
            subject=self.subject,
            teacher=self.teacher,
            weekday=WeeklySchedule.Weekday.WEDNESDAY,
            starts_at=time(7, 20),
            ends_at=time(8, 0),
            entry_type=WeeklySchedule.EntryType.CLASS,
        )
        with self.assertRaises(ValidationError):
            conflicting.full_clean()

    def test_seed_scheduler_generates_non_conflicting_schedule(self):
        history_teacher = User.objects.create_user(
            email="history@educas.com",
            password="12345678",
            first_name="Helena",
            role=User.Role.TEACHER,
        )
        history = Subject.objects.create(code="HIS202", name="Historia Avancada")
        science = Subject.objects.create(code="BIO202", name="Biologia Aplicada")
        science_teacher = User.objects.create_user(
            email="science@educas.com",
            password="12345678",
            first_name="Rita",
            role=User.Role.TEACHER,
        )
        assignments = [
            ClassroomSubject.objects.get(classroom=self.classroom, subject=self.subject),
            ClassroomSubject.objects.create(classroom=self.classroom, subject=history, teacher=history_teacher),
            ClassroomSubject.objects.create(classroom=self.classroom, subject=science, teacher=science_teacher),
        ]

        command = SeedInstitutionalCommand()
        command._seed_weekly_schedule(classroom=self.classroom, classroom_position=0, assignments=assignments)

        class_entries = WeeklySchedule.objects.filter(
            classroom=self.classroom,
            entry_type=WeeklySchedule.EntryType.CLASS,
        ).order_by("weekday", "starts_at")
        self.assertGreaterEqual(class_entries.count(), len(assignments))
        for entry in class_entries:
            entry.full_clean()

    def test_closed_assignment_blocks_new_submission(self):
        closed_assignment = Assignment.objects.create(
            classroom=self.classroom,
            subject=self.subject,
            author=self.teacher,
            title="Atividade Encerrada",
            description="Prazo vencido.",
            due_at=timezone.now() - timedelta(minutes=1),
        )
        closed_assignment.close_if_expired()
        submission = Submission(
            assignment=closed_assignment,
            student=self.student,
            text_answer="Envio atrasado",
        )
        with self.assertRaises(ValidationError):
            submission.full_clean()

    def test_ai_generation_falls_back_without_key(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            payload, meta = generate_json(
                prompt="Teste curto",
                fallback={
                    "first_names": ["Ana"],
                    "last_names": ["Silva"],
                    "teacher_messages": ["Mensagem de teste."],
                    "student_comments": ["Comentario de teste."],
                },
            )
        self.assertEqual(meta["provider"], "fallback")
        self.assertFalse(meta["used_api"])
        self.assertEqual(payload["first_names"], ["Ana"])

    def test_ai_configuration_reads_runtime_environment(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "runtime-test-key",
                "OPENROUTER_MODEL": "openai/test-model",
            },
            clear=False,
        ):
            config_data = get_ai_configuration()
        self.assertTrue(config_data["enabled"])
        self.assertEqual(config_data["api_key"], "runtime-test-key")
        self.assertEqual(config_data["model"], "openai/test-model")
