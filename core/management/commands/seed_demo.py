from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from academics.models import AcademicEvent, AcademicYear, Attendance, Classroom, ClassroomSubject, Enrollment, Grade, GradeLevel, Subject
from assignments.models import Assignment, Submission
from engagement.models import Comment, Post, PostReaction


class Command(BaseCommand):
    help = "Cria uma base demo coerente com a arquitetura nova do Educas."

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            email="admin@educas.local",
            defaults={
                "first_name": "Admin",
                "last_name": "Educas",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("admin12345")
        admin.save()

        teacher, _ = User.objects.get_or_create(
            email="prof.roberto@educas.local",
            defaults={"first_name": "Roberto", "last_name": "Santos", "role": User.Role.TEACHER},
        )
        teacher.set_password("prof12345")
        teacher.save()

        student, _ = User.objects.get_or_create(
            email="aluno.thiallisson@educas.local",
            defaults={"first_name": "Thiallisson", "last_name": "Oliveira", "role": User.Role.STUDENT},
        )
        student.set_password("aluno12345")
        student.save()

        math, _ = Subject.objects.get_or_create(code="MAT301", defaults={"name": "Matematica"})
        history, _ = Subject.objects.get_or_create(code="HIS301", defaults={"name": "Historia"})

        academic_year, _ = AcademicYear.objects.get_or_create(
            year=timezone.now().year,
            defaults={"name": str(timezone.now().year), "is_active": True},
        )
        grade_level, _ = GradeLevel.objects.get_or_create(
            code="3EM",
            defaults={
                "name": "3o Ano EM",
                "stage": GradeLevel.EducationStage.HIGH_SCHOOL,
                "sequence": 12,
                "is_active": True,
            },
        )

        classroom, _ = Classroom.objects.get_or_create(
            name="3 Ano B",
            school_year=timezone.now().year,
            section="B",
            defaults={
                "created_by": admin,
                "homeroom_teacher": teacher,
                "academic_year": academic_year,
                "grade_level": grade_level,
                "shift": Classroom.Shift.MORNING,
            },
        )
        classroom.homeroom_teacher = teacher
        classroom.created_by = admin
        classroom.academic_year = academic_year
        classroom.grade_level = grade_level
        classroom.shift = Classroom.Shift.MORNING
        classroom.save()

        ClassroomSubject.objects.get_or_create(classroom=classroom, subject=math, defaults={"teacher": teacher})
        ClassroomSubject.objects.get_or_create(classroom=classroom, subject=history, defaults={"teacher": teacher})

        Enrollment.objects.get_or_create(
            student=student,
            classroom=classroom,
            defaults={"status": Enrollment.Status.APPROVED, "approved_by": admin, "approved_at": timezone.now()},
        )

        Grade.objects.get_or_create(
            classroom=classroom,
            student=student,
            subject=math,
            assessment_name="AV1",
            defaults={"assessment_type": Grade.AssessmentType.EXAM, "score": 8.5, "recorded_by": teacher},
        )

        Attendance.objects.get_or_create(
            classroom=classroom,
            student=student,
            subject=math,
            date=timezone.localdate(),
            defaults={"status": Attendance.Status.PRESENT, "marked_by": teacher},
        )

        event, _ = AcademicEvent.objects.get_or_create(
            classroom=classroom,
            subject=math,
            title="Simulado de Matematica",
            defaults={
                "created_by": teacher,
                "description": "Simulado preparatorio.",
                "starts_at": timezone.now() + timedelta(days=2),
                "event_type": AcademicEvent.EventType.EXAM,
            },
        )

        post, _ = Post.objects.get_or_create(
            classroom=classroom,
            author=teacher,
            title="Material de revisao",
            defaults={
                "subject": math,
                "post_type": Post.PostType.MATERIAL,
                "content": "Resumo e lista comentada para a proxima avaliacao.",
                "is_pinned": True,
            },
        )

        Comment.objects.get_or_create(post=post, author=student, defaults={"content": "Material muito bom para revisar."})
        PostReaction.objects.get_or_create(post=post, user=student)

        assignment, _ = Assignment.objects.get_or_create(
            classroom=classroom,
            subject=history,
            author=teacher,
            title="Resumo da Revolucao Industrial",
            defaults={
                "description": "Entregar resumo em uma pagina.",
                "due_at": timezone.now() + timedelta(days=5),
                "points": 10,
            },
        )

        Submission.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={
                "text_answer": "Resumo inicial entregue em texto.",
                "status": Submission.Status.SUBMITTED,
                "submitted_at": timezone.now(),
            },
        )

        self.stdout.write(self.style.SUCCESS("Base demo criada. Admin: admin@educas.local / admin12345"))
