from datetime import time, timedelta
from decimal import Decimal
from itertools import cycle

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import StudentProfile, TeacherProfile, User
from academics.models import (
    AcademicEvent,
    AcademicYear,
    Attendance,
    Classroom,
    ClassroomSubject,
    Enrollment,
    Grade,
    GradeLevel,
    Subject,
    WeeklySchedule,
)
from assignments.models import Assignment, Submission
from common.ai_content import generate_json
from engagement.models import Comment, Post, PostReaction


class Command(BaseCommand):
    help = "Gera massa institucional profissional, coerente e idempotente para o Educas."

    ADMIN_PASSWORD = "admin123"
    TEACHER_PASSWORD = "Professor@2026"
    STUDENT_PASSWORD = "Aluno@2026"
    MANAGED_TAG = "[educas-seed]"

    SHIFT_SLOT_MAP = {
        Classroom.Shift.MORNING: {
            "class_slots": [
                (time(7, 0), time(7, 50)),
                (time(7, 50), time(8, 40)),
                (time(9, 0), time(9, 50)),
                (time(9, 50), time(10, 40)),
                (time(11, 0), time(11, 50)),
                (time(11, 50), time(12, 40)),
            ],
            "breaks": [(time(8, 40), time(9, 0)), (time(10, 40), time(11, 0))],
        },
        Classroom.Shift.AFTERNOON: {
            "class_slots": [
                (time(13, 0), time(13, 50)),
                (time(13, 50), time(14, 40)),
                (time(15, 0), time(15, 50)),
                (time(15, 50), time(16, 40)),
                (time(17, 0), time(17, 50)),
                (time(17, 50), time(18, 40)),
            ],
            "breaks": [(time(14, 40), time(15, 0)), (time(16, 40), time(17, 0))],
        },
    }

    WEEKDAY_ORDER = [
        WeeklySchedule.Weekday.MONDAY,
        WeeklySchedule.Weekday.TUESDAY,
        WeeklySchedule.Weekday.WEDNESDAY,
        WeeklySchedule.Weekday.THURSDAY,
        WeeklySchedule.Weekday.FRIDAY,
    ]

    SUBJECT_DEFINITIONS = [
        ("MAT101", "Matematica"),
        ("POR101", "Portugues"),
        ("HIS101", "Historia"),
        ("GEO101", "Geografia"),
        ("BIO101", "Biologia"),
        ("FIS101", "Fisica"),
        ("QUI101", "Quimica"),
        ("RED101", "Redacao"),
        ("ART101", "Artes"),
        ("FIL101", "Filosofia"),
        ("EDU101", "Educacao Fisica"),
        ("ING101", "Ingles"),
    ]

    GRADE_DEFINITIONS = [
        ("1EF", "1o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_I, 1),
        ("2EF", "2o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_I, 2),
        ("3EF", "3o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_I, 3),
        ("4EF", "4o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_I, 4),
        ("5EF", "5o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_I, 5),
        ("6EF", "6o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_II, 6),
        ("7EF", "7o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_II, 7),
        ("8EF", "8o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_II, 8),
        ("9EF", "9o Ano EF", GradeLevel.EducationStage.FUNDAMENTAL_II, 9),
        ("1EM", "1o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 10),
        ("2EM", "2o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 11),
        ("3EM", "3o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 12),
    ]

    TEACHER_BLUEPRINTS = [
        ("ana.beatriz", "Ana", "Beatriz", ["FI_HUMAN"], "Alfabetizacao e linguagens"),
        ("maria.clara", "Maria", "Clara", ["FI_HUMAN"], "Projetos integrados de Fundamental I"),
        ("luciana.rocha", "Luciana", "Rocha", ["FI_HUMAN"], "Leitura, artes e producao textual"),
        ("bruno.castro", "Bruno", "Castro", ["FI_STEM"], "Matematica e ciencias no Fundamental I"),
        ("diego.moura", "Diego", "Moura", ["FI_STEM"], "Ciencias, logica e educacao fisica"),
        ("carla.nogueira", "Carla", "Nogueira", ["FI_STEM"], "Projetos de matematica e observacao cientifica"),
        ("carlos.silva", "Carlos", "Silva", ["MAT101"], "Matematica"),
        ("joao.costa", "Joao", "Costa", ["MAT101"], "Matematica aplicada"),
        ("ana.souza", "Ana", "Souza", ["POR101", "RED101"], "Linguagens e redacao"),
        ("beatriz.ferreira", "Beatriz", "Ferreira", ["POR101", "RED101"], "Literatura e producao textual"),
        ("paula.rocha", "Paula", "Rocha", ["HIS101", "FIL101"], "Historia e filosofia"),
        ("fernando.bastos", "Fernando", "Bastos", ["HIS101", "GEO101"], "Historia e geografia"),
        ("lucas.melo", "Lucas", "Melo", ["GEO101", "ING101"], "Geografia e ingles"),
        ("marina.almeida", "Marina", "Almeida", ["BIO101"], "Biologia"),
        ("julia.nascimento", "Julia", "Nascimento", ["BIO101", "QUI101"], "Biologia e quimica"),
        ("ricardo.lima", "Ricardo", "Lima", ["FIS101"], "Fisica"),
        ("joana.pires", "Joana", "Pires", ["QUI101"], "Quimica"),
        ("marcos.vieira", "Marcos", "Vieira", ["EDU101"], "Educacao fisica"),
        ("renata.lopes", "Renata", "Lopes", ["ART101"], "Artes"),
    ]

    def handle(self, *args, **options):
        payload, meta = generate_json(
            prompt=(
                "Gere JSON com as chaves first_names, last_names, teacher_messages, student_comments, event_titles e guardian_names. "
                "Tudo em portugues do Brasil, com tom escolar realista e profissional."
            ),
            fallback={
                "first_names": [
                    "Ana", "Bruno", "Camila", "Daniel", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "Joao",
                    "Karina", "Lucas", "Mariana", "Nicolas", "Olivia", "Pedro", "Rafael", "Sofia", "Tiago", "Yasmin",
                    "Amanda", "Beatriz", "Caio", "Diego", "Elisa", "Fernanda", "Guilherme", "Helena", "Igor", "Julia",
                ],
                "last_names": [
                    "Silva", "Souza", "Oliveira", "Costa", "Santos", "Lima", "Almeida", "Rocha", "Carvalho", "Melo",
                    "Barbosa", "Martins", "Gomes", "Ferreira", "Teixeira", "Pereira", "Araujo", "Nascimento", "Freitas", "Batista",
                ],
                "teacher_messages": [
                    "Pessoal, revisem o material da semana e anotem as dúvidas para a próxima aula.",
                    "Lembrem-se de acompanhar o cronograma e organizar a entrega com antecedência.",
                    "A atividade já está no mural com orientações claras e prazo definido.",
                    "Quem precisar de apoio pode comentar no post ou falar comigo no início da aula.",
                    "Hoje vamos consolidar o conteúdo com exercícios práticos e revisão guiada.",
                ],
                "student_comments": [
                    "Professor, já comecei a organizar minha entrega.",
                    "Obrigado pelo aviso, vou revisar o conteúdo hoje.",
                    "Consegui acessar o material e já separei minhas dúvidas.",
                    "Vou levar o caderno atualizado para a próxima aula.",
                    "Entendi o cronograma, obrigado pela orientação.",
                ],
                "event_titles": [
                    "Simulado parcial",
                    "Aula de revisão",
                    "Entrega de atividade",
                    "Avaliação escrita",
                    "Apresentação de trabalho",
                ],
                "guardian_names": [
                    "Maria de Lourdes", "José Carlos", "Patrícia Andrade", "Roberto Almeida", "Cláudia Lima",
                ],
            },
        )

        self.stdout.write(
            self.style.NOTICE(
                f"Seed institucional usando provedor: {meta['provider']} | API ativa: {meta['used_api']}"
            )
        )

        with transaction.atomic():
            self._remove_placeholder_data()
            academic_year = self._ensure_academic_year()
            subjects = self._ensure_subjects()
            grade_levels = self._ensure_grade_levels()
            admin = self._ensure_admin()
            teacher_pool, managed_teacher_ids = self._ensure_teachers()
            classrooms = self._ensure_classrooms(academic_year, grade_levels, teacher_pool)
            students, managed_student_ids = self._ensure_students(payload["first_names"], payload["last_names"], payload["guardian_names"])
            self._reset_managed_academic_data(classrooms, managed_teacher_ids, managed_student_ids)
            assignments_by_classroom = self._assign_subjects_and_teachers(classrooms, subjects, teacher_pool)
            for position, classroom in enumerate(classrooms):
                self._seed_weekly_schedule(
                    classroom=classroom,
                    classroom_position=position,
                    assignments=assignments_by_classroom[classroom.id],
                )
            self._enroll_students(students, classrooms, admin)
            self._seed_classroom_activity(classrooms, payload["teacher_messages"], payload["student_comments"], payload["event_titles"])

        self.stdout.write(
            self.style.SUCCESS(
                "Seed institucional concluído com turmas reais, horários válidos, professores coerentes e mural organizado."
            )
        )

    def _ensure_academic_year(self):
        year = timezone.now().year
        academic_year, _ = AcademicYear.objects.get_or_create(
            year=year,
            defaults={"name": str(year), "is_active": True},
        )
        return academic_year

    def _ensure_admin(self):
        admin, _ = User.objects.get_or_create(
            email="admin@educas.com",
            defaults={
                "first_name": "Administrador",
                "last_name": "Educas",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "is_verified": True,
            },
        )
        admin.set_password(self.ADMIN_PASSWORD)
        admin.save()
        return admin

    def _ensure_subjects(self):
        subjects = {}
        for code, name in self.SUBJECT_DEFINITIONS:
            subjects[code], _ = Subject.objects.get_or_create(code=code, defaults={"name": name, "is_active": True})
        return subjects

    def _ensure_grade_levels(self):
        grade_levels = {}
        for code, name, stage, sequence in self.GRADE_DEFINITIONS:
            grade_levels[code], _ = GradeLevel.objects.get_or_create(
                code=code,
                defaults={"name": name, "stage": stage, "sequence": sequence, "is_active": True},
            )
        return grade_levels

    def _ensure_teachers(self):
        teacher_pool = {}
        managed_ids = []
        for index, (slug, first_name, last_name, specialties, expertise) in enumerate(self.TEACHER_BLUEPRINTS, start=1):
            teacher, _ = User.objects.get_or_create(
                email=f"{slug}@educas.edu.br",
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.TEACHER,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            teacher.first_name = first_name
            teacher.last_name = last_name
            teacher.role = User.Role.TEACHER
            teacher.is_active = True
            teacher.is_verified = True
            teacher.set_password(self.TEACHER_PASSWORD)
            teacher.save()
            TeacherProfile.objects.update_or_create(
                user=teacher,
                defaults={
                    "employee_code": f"PRF-2026-{index:03d}",
                    "expertise": expertise,
                },
            )
            for specialty in specialties:
                teacher_pool.setdefault(specialty, []).append(teacher)
            managed_ids.append(teacher.id)
        return teacher_pool, managed_ids

    def _ensure_students(self, first_names, last_names, guardian_names):
        students = []
        managed_ids = []
        total_students = 120
        for index in range(1, total_students + 1):
            first_name = first_names[(index - 1) % len(first_names)]
            last_name = last_names[((index * 3) - 1) % len(last_names)]
            email_slug = slugify(f"{first_name}-{last_name}") or f"aluno-{index:03d}"
            email = f"{email_slug}{index:03d}@educas.edu.br"
            guardian_name = guardian_names[(index - 1) % len(guardian_names)]
            student, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.STUDENT,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            student.first_name = first_name
            student.last_name = last_name
            student.role = User.Role.STUDENT
            student.is_active = True
            student.is_verified = True
            student.set_password(self.STUDENT_PASSWORD)
            student.save()
            StudentProfile.objects.update_or_create(
                user=student,
                defaults={
                    "registration_code": f"ALN-2026-{index:03d}",
                    "guardian_name": guardian_name,
                    "guardian_phone": f"(86) 9{(index % 9000) + 1000:04d}-{(index % 9000) + 2000:04d}",
                },
            )
            students.append(student)
            managed_ids.append(student.id)
        return students, managed_ids

    def _ensure_classrooms(self, academic_year, grade_levels, teacher_pool):
        classrooms = []
        fund_i_teacher_cycle = cycle(teacher_pool["FI_HUMAN"] + teacher_pool["FI_STEM"])
        subject_teacher_cycle = cycle(teacher_pool["POR101"] + teacher_pool["MAT101"] + teacher_pool["HIS101"])
        for grade_code, _name, stage, _sequence in self.GRADE_DEFINITIONS:
            for shift, section in ((Classroom.Shift.MORNING, "A"), (Classroom.Shift.AFTERNOON, "B")):
                if stage == GradeLevel.EducationStage.HIGH_SCHOOL:
                    name = f"{grade_code}-{section}"
                else:
                    name = f"{grade_code}-{section}"
                homeroom_teacher = next(fund_i_teacher_cycle if stage == GradeLevel.EducationStage.FUNDAMENTAL_I else subject_teacher_cycle)
                classroom, _ = Classroom.objects.get_or_create(
                    name=name,
                    school_year=academic_year.year,
                    section=section,
                    defaults={
                        "academic_year": academic_year,
                        "grade_level": grade_levels[grade_code],
                        "shift": shift,
                        "homeroom_teacher": homeroom_teacher,
                        "created_by": homeroom_teacher,
                        "is_active": True,
                    },
                )
                classroom.academic_year = academic_year
                classroom.grade_level = grade_levels[grade_code]
                classroom.shift = shift
                classroom.homeroom_teacher = homeroom_teacher
                classroom.created_by = homeroom_teacher
                classroom.is_active = True
                classroom.save()
                classrooms.append(classroom)
        return classrooms

    def _reset_managed_academic_data(self, classrooms, managed_teacher_ids, managed_student_ids):
        classroom_ids = [classroom.id for classroom in classrooms]
        Post.objects.filter(classroom_id__in=classroom_ids, author_id__in=managed_teacher_ids).delete()
        Assignment.objects.filter(classroom_id__in=classroom_ids, author_id__in=managed_teacher_ids).delete()
        AcademicEvent.objects.filter(classroom_id__in=classroom_ids, created_by_id__in=managed_teacher_ids).delete()
        WeeklySchedule.objects.filter(classroom_id__in=classroom_ids).delete()
        ClassroomSubject.objects.filter(classroom_id__in=classroom_ids).delete()
        Grade.objects.filter(classroom_id__in=classroom_ids, student_id__in=managed_student_ids).delete()
        Attendance.objects.filter(classroom_id__in=classroom_ids, student_id__in=managed_student_ids).delete()
        Enrollment.objects.filter(classroom_id__in=classroom_ids, student_id__in=managed_student_ids).delete()

    def _remove_placeholder_data(self):
        fake_users = User.objects.filter(
            Q(first_name__icontains="aluno")
            | Q(first_name__icontains="teste")
            | Q(email__icontains="teste123")
            | Q(email__icontains="user123")
            | Q(email__icontains="placeholder")
        ).exclude(email="admin@educas.com")
        fake_users.delete()

        Post.objects.filter(
            Q(title__icontains="teste") | Q(content__icontains="placeholder") | Q(content__icontains="lorem")
        ).delete()

    def _subject_codes_for_stage(self, stage):
        return {
            GradeLevel.EducationStage.FUNDAMENTAL_I: ["MAT101", "POR101", "HIS101", "GEO101", "ART101", "EDU101"],
            GradeLevel.EducationStage.FUNDAMENTAL_II: ["MAT101", "POR101", "HIS101", "GEO101", "BIO101", "EDU101"],
            GradeLevel.EducationStage.HIGH_SCHOOL: ["MAT101", "POR101", "FIS101", "QUI101", "RED101", "ING101"],
        }[stage]

    def _workload_map_for_stage(self, stage):
        if stage == GradeLevel.EducationStage.FUNDAMENTAL_I:
            return {"MAT101": 6, "POR101": 8, "HIS101": 4, "GEO101": 4, "ART101": 4, "EDU101": 4}
        if stage == GradeLevel.EducationStage.FUNDAMENTAL_II:
            return {"MAT101": 6, "POR101": 6, "HIS101": 5, "GEO101": 5, "BIO101": 4, "EDU101": 4}
        return {"MAT101": 6, "POR101": 5, "FIS101": 5, "QUI101": 5, "RED101": 5, "ING101": 4}

    def _teacher_keys_for_subject(self, stage, subject_code):
        if stage == GradeLevel.EducationStage.FUNDAMENTAL_I:
            if subject_code in {"POR101", "HIS101", "GEO101", "ART101"}:
                return ["FI_HUMAN"]
            return ["FI_STEM"]
        if subject_code == "RED101":
            return ["POR101", "RED101"]
        return [subject_code]

    def _pick_teacher(self, teacher_pool, stage, subject_code, classroom_index):
        for pool_key in self._teacher_keys_for_subject(stage, subject_code):
            candidates = teacher_pool.get(pool_key, [])
            if candidates:
                return candidates[classroom_index % len(candidates)]
        fallback_pool = next(iter(teacher_pool.values()))
        return fallback_pool[classroom_index % len(fallback_pool)]

    def _assign_subjects_and_teachers(self, classrooms, subjects, teacher_pool):
        assignments_by_classroom = {}
        for classroom_index, classroom in enumerate(classrooms):
            assignments = []
            for subject_code in self._subject_codes_for_stage(classroom.grade_level.stage):
                teacher = self._pick_teacher(teacher_pool, classroom.grade_level.stage, subject_code, classroom_index)
                classroom_subject, _ = ClassroomSubject.objects.get_or_create(
                    classroom=classroom,
                    subject=subjects[subject_code],
                    defaults={
                        "teacher": teacher,
                        "weekly_workload": self._workload_map_for_stage(classroom.grade_level.stage)[subject_code],
                    },
                )
                classroom_subject.teacher = teacher
                classroom_subject.weekly_workload = self._workload_map_for_stage(classroom.grade_level.stage)[subject_code]
                classroom_subject.save()
                assignments.append(classroom_subject)
            assignments_by_classroom[classroom.id] = assignments
        return assignments_by_classroom

    def _seed_weekly_schedule(self, *, classroom, classroom_position, assignments):
        shift_config = self.SHIFT_SLOT_MAP[classroom.shift]
        self._ensure_break_slots(classroom, shift_config["breaks"])
        weighted_assignments = []
        workload_map = self._workload_map_for_stage(classroom.grade_level.stage)
        assignment_lookup = {assignment.subject.code: assignment for assignment in assignments}
        for subject_code, workload in workload_map.items():
            assignment = assignment_lookup.get(subject_code)
            if assignment:
                weighted_assignments.extend([assignment] * workload)
        if not weighted_assignments:
            for assignment in assignments:
                weighted_assignments.extend([assignment] * max(1, assignment.weekly_workload))
        rotated = weighted_assignments[classroom_position % len(weighted_assignments):] + weighted_assignments[:classroom_position % len(weighted_assignments)]
        assignment_cycle = cycle(rotated)

        for weekday in self.WEEKDAY_ORDER:
            previous_subject_code = None
            for starts_at, ends_at in shift_config["class_slots"]:
                selected_assignment = self._pick_available_assignment(
                    assignment_cycle=assignment_cycle,
                    candidates=rotated,
                    classroom=classroom,
                    weekday=weekday,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    previous_subject_code=previous_subject_code,
                )
                if selected_assignment is None:
                    continue
                WeeklySchedule.objects.create(
                    classroom=classroom,
                    weekday=weekday,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    entry_type=WeeklySchedule.EntryType.CLASS,
                    subject=selected_assignment.subject,
                    teacher=selected_assignment.teacher,
                    room_label=f"Sala {classroom.section}",
                )
                previous_subject_code = selected_assignment.subject.code

    def _pick_available_assignment(
        self,
        *,
        assignment_cycle,
        candidates,
        classroom,
        weekday,
        starts_at,
        ends_at,
        previous_subject_code,
    ):
        for _ in range(len(candidates) * 2):
            assignment = next(assignment_cycle)
            if previous_subject_code == assignment.subject.code:
                continue
            if self._slot_is_available(
                classroom=classroom,
                teacher=assignment.teacher,
                weekday=weekday,
                starts_at=starts_at,
                ends_at=ends_at,
            ):
                return assignment
        return None

    def _ensure_break_slots(self, classroom, breaks):
        for weekday in self.WEEKDAY_ORDER:
            for starts_at, ends_at in breaks:
                WeeklySchedule.objects.create(
                    classroom=classroom,
                    weekday=weekday,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    entry_type=WeeklySchedule.EntryType.BREAK,
                    room_label="Intervalo",
                )

    def _slot_is_available(self, *, classroom, teacher, weekday, starts_at, ends_at):
        overlap_filter = Q(starts_at__lt=ends_at, ends_at__gt=starts_at)
        if WeeklySchedule.objects.filter(classroom=classroom, weekday=weekday).filter(overlap_filter).exists():
            return False
        if WeeklySchedule.objects.filter(
            teacher=teacher,
            weekday=weekday,
            entry_type=WeeklySchedule.EntryType.CLASS,
        ).filter(overlap_filter).exists():
            return False
        return True

    def _enroll_students(self, students, classrooms, admin):
        classroom_cycle = cycle(classrooms)
        for student in students:
            classroom = next(classroom_cycle)
            Enrollment.objects.create(
                student=student,
                classroom=classroom,
                status=Enrollment.Status.APPROVED,
                approved_by=admin,
                approved_at=timezone.now(),
            )

    def _seed_classroom_activity(self, classrooms, teacher_messages, student_comments, event_titles):
        base_date = timezone.now()
        for classroom_index, classroom in enumerate(classrooms):
            classroom_students = list(
                User.objects.filter(enrollments__classroom=classroom, enrollments__status=Enrollment.Status.APPROVED)
                .select_related("student_profile")
                .order_by("first_name")[:5]
            )
            classroom_subjects = list(
                ClassroomSubject.objects.filter(classroom=classroom).select_related("subject", "teacher").order_by("subject__name")
            )
            for subject_index, classroom_subject in enumerate(classroom_subjects):
                post_time = base_date - timedelta(hours=(classroom_index * 3) + subject_index)
                due_at = base_date + timedelta(days=7 + subject_index + (classroom_index % 4))
                assignment = Assignment.objects.create(
                    classroom=classroom,
                    subject=classroom_subject.subject,
                    author=classroom_subject.teacher,
                    title=f"Atividade {classroom_subject.subject.name} - {classroom.name}",
                    description=f"{teacher_messages[subject_index % len(teacher_messages)]} {self.MANAGED_TAG}",
                    due_at=due_at,
                    points=Decimal("10.00"),
                )
                post = Post.objects.create(
                    classroom=classroom,
                    author=classroom_subject.teacher,
                    subject=classroom_subject.subject,
                    post_type=Post.PostType.ANNOUNCEMENT if subject_index % 2 == 0 else Post.PostType.MATERIAL,
                    title=f"{classroom_subject.subject.name} | {classroom.name}",
                    content=f"{teacher_messages[(classroom_index + subject_index) % len(teacher_messages)]} {self.MANAGED_TAG}",
                    is_pinned=subject_index == 0,
                )
                Post.objects.filter(pk=post.pk).update(created_at=post_time, updated_at=post_time)
                event_start = due_at + timedelta(days=2)
                AcademicEvent.objects.create(
                    classroom=classroom,
                    subject=classroom_subject.subject,
                    created_by=classroom_subject.teacher,
                    title=f"{event_titles[(classroom_index + subject_index) % len(event_titles)]} - {classroom_subject.subject.name}",
                    description=f"Evento acadêmico planejado para {classroom.name}. {self.MANAGED_TAG}",
                    starts_at=event_start,
                    ends_at=event_start + timedelta(hours=1),
                    event_type=AcademicEvent.EventType.EXAM if subject_index % 2 == 0 else AcademicEvent.EventType.DEADLINE,
                )

                for student_index, student in enumerate(classroom_students):
                    Comment.objects.create(
                        post=post,
                        author=student,
                        content=f"{student_comments[(student_index + subject_index) % len(student_comments)]} {self.MANAGED_TAG}",
                    )
                    PostReaction.objects.get_or_create(post=post, user=student)
                    Submission.objects.create(
                        assignment=assignment,
                        student=student,
                        text_answer="Entrega inicial registrada no seed institucional.",
                        status=Submission.Status.SUBMITTED,
                        submitted_at=post_time + timedelta(days=1),
                    )
                    Grade.objects.create(
                        classroom=classroom,
                        student=student,
                        subject=classroom_subject.subject,
                        recorded_by=classroom_subject.teacher,
                        assessment_name=f"AV-{classroom_subject.subject.code}",
                        assessment_type=Grade.AssessmentType.HOMEWORK,
                        term=Grade.Term.BIMESTER_1,
                        score=Decimal(str(7 + ((student_index + subject_index) % 3))),
                        max_score=Decimal("10.00"),
                        weight=Decimal("1.00"),
                    )
                    for day_offset in range(2):
                        attendance_date = timezone.localdate() - timedelta(days=day_offset + subject_index + 1)
                        Attendance.objects.get_or_create(
                            classroom=classroom,
                            student=student,
                            subject=classroom_subject.subject,
                            date=attendance_date,
                            defaults={
                                "term": Grade.Term.BIMESTER_1,
                                "status": Attendance.Status.PRESENT if (student_index + day_offset) % 5 else Attendance.Status.ABSENT,
                                "marked_by": classroom_subject.teacher,
                                "notes": f"Registro institucional inicial. {self.MANAGED_TAG}",
                            },
                        )
