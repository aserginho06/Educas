from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
import secrets
import string


def generate_access_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class AcademicYear(models.Model):
    year = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=40, blank=True)
    starts_on = models.DateField(blank=True, null=True)
    ends_on = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-year"]

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = str(self.year)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GradeLevel(models.Model):
    class EducationStage(models.TextChoices):
        FUNDAMENTAL_I = "fundamental_i", "Ensino Fundamental I"
        FUNDAMENTAL_II = "fundamental_ii", "Ensino Fundamental II"
        HIGH_SCHOOL = "high_school", "Ensino Medio"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=60, unique=True)
    stage = models.CharField(max_length=30, choices=EducationStage.choices)
    sequence = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["stage", "sequence", "name"]

    def __str__(self):
        return self.name


class Classroom(models.Model):
    class Shift(models.TextChoices):
        MORNING = "morning", "Manha"
        AFTERNOON = "afternoon", "Tarde"
        EVENING = "evening", "Noite"
        FULL_TIME = "full_time", "Integral"

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    access_code = models.CharField(max_length=12, unique=True, default=generate_access_code, editable=False)
    school_year = models.PositiveIntegerField()
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="classrooms",
        null=True,
        blank=True,
    )
    grade_level = models.ForeignKey(
        GradeLevel,
        on_delete=models.PROTECT,
        related_name="classrooms",
        null=True,
        blank=True,
    )
    section = models.CharField(max_length=20, blank=True)
    shift = models.CharField(max_length=20, choices=Shift.choices, default=Shift.MORNING)
    is_active = models.BooleanField(default=True)
    homeroom_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="homeroom_classrooms",
        limit_choices_to={"role": "teacher"},
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_classrooms",
    )
    subjects = models.ManyToManyField(Subject, through="ClassroomSubject", related_name="classrooms")

    class Meta:
        ordering = ["-school_year", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "school_year", "section"], name="uniq_classroom_year_section")
        ]
        indexes = [
            models.Index(fields=["school_year", "is_active"]),
            models.Index(fields=["shift", "is_active"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["access_code"]),
        ]

    def save(self, *args, **kwargs):
        if self.academic_year_id:
            self.school_year = self.academic_year.year
        if not self.slug:
            slug_base = self.grade_level.code if self.grade_level_id else self.name
            self.slug = slugify(f"{slug_base}-{self.school_year}-{self.section or self.shift}")
        super().save(*args, **kwargs)

    @property
    def institutional_label(self):
        parts = [
            self.grade_level.name if self.grade_level_id else self.name,
            self.section or self.name,
        ]
        return " ".join(part for part in parts if part).strip()

    def __str__(self):
        return f"{self.name} {self.section} - {self.school_year}".strip()


class ClassroomSubject(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="classroom_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="classroom_subjects")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        limit_choices_to={"role": "teacher"},
    )
    weekly_workload = models.PositiveSmallIntegerField(default=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["classroom", "subject"], name="uniq_subject_per_classroom")
        ]
        indexes = [models.Index(fields=["teacher", "classroom"])]

    def __str__(self):
        return f"{self.classroom} - {self.subject}"


class Lesson(models.Model):
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lessons",
        limit_choices_to={"role": "teacher"},
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="lessons")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="lessons")
    date = models.DateField()
    quantidade_aulas = models.PositiveSmallIntegerField(default=1)
    conteudo = models.TextField()
    atividade = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["professor", "classroom", "subject", "date"])]

    def __str__(self):
        return f"{self.date} • {self.classroom.name} • {self.subject.name}"


class AttendanceRecord(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_attendance_records",
        limit_choices_to={"role": "student"},
    )
    absences = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lesson", "student"]
        constraints = [
            models.UniqueConstraint(fields=["lesson", "student"], name="uniq_attendance_record_per_lesson_student")
        ]
        indexes = [models.Index(fields=["lesson", "student"]), models.Index(fields=["student"])]

    def __str__(self):
        return f"{self.lesson} • {self.student} • {self.absences} faltas"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"
        REJECTED = "rejected", "Rejeitada"
        CANCELED = "canceled", "Cancelada"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "student"},
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_enrollments",
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "classroom"], name="uniq_student_classroom")]
        indexes = [models.Index(fields=["status", "classroom"]), models.Index(fields=["student", "status"])]

    def clean(self):
        conflicting = Enrollment.objects.filter(
            student=self.student,
            classroom__school_year=self.classroom.school_year,
            classroom__shift=self.classroom.shift,
            status=self.Status.APPROVED,
        ).exclude(pk=self.pk)
        if conflicting.exists() and self.status == self.Status.APPROVED:
            raise ValidationError("O aluno nao pode estar em duas turmas no mesmo turno e ano letivo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} em {self.classroom}"


class Grade(models.Model):
    class AssessmentType(models.TextChoices):
        EXAM = "exam", "Prova"
        PROJECT = "project", "Projeto"
        HOMEWORK = "homework", "Atividade"
        PARTICIPATION = "participation", "Participacao"

    class Term(models.TextChoices):
        BIMESTER_1 = "b1", "1o Bimestre"
        BIMESTER_2 = "b2", "2o Bimestre"
        BIMESTER_3 = "b3", "3o Bimestre"
        BIMESTER_4 = "b4", "4o Bimestre"
        RECOVERY = "recovery", "Recuperacao"

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grades",
        limit_choices_to={"role": "student"},
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="grades")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_grades",
        limit_choices_to={"role": "teacher"},
    )
    assessment_name = models.CharField(max_length=120)
    assessment_type = models.CharField(max_length=20, choices=AssessmentType.choices, default=AssessmentType.HOMEWORK)
    term = models.CharField(max_length=20, choices=Term.choices, default=Term.BIMESTER_1)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-graded_at"]
        indexes = [models.Index(fields=["classroom", "student"]), models.Index(fields=["subject", "student"])]

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.score}"


class Assessment(models.Model):
    class AssessmentType(models.TextChoices):
        P1 = "P1", "P1"
        REC1 = "REC1", "REC1"
        P2 = "P2", "P2"
        REC2 = "REC2", "REC2"
        P3 = "P3", "P3"
        REC3 = "REC3", "REC3"
        P4 = "P4", "P4"
        REC4 = "REC4", "REC4"
        FINAL = "FINAL", "FINAL"

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessments",
        limit_choices_to={"role": "teacher"},
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="assessments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assessments")
    assessment_type = models.CharField(max_length=10, choices=AssessmentType.choices)
    date = models.DateField()
    description = models.TextField(blank=True)
    quantidade_aulas = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "subject", "assessment_type"]
        indexes = [models.Index(fields=["professor", "classroom", "subject", "assessment_type"])]

    def __str__(self):
        return f"{self.assessment_type} - {self.subject.name} - {self.classroom.name}"


class GradeEntry(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="grade_entries")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grade_entries",
        limit_choices_to={"role": "student"},
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def score_display(self):
        return format(self.score, ".1f") if self.score is not None else None

    class Meta:
        ordering = ["assessment", "student"]
        constraints = [
            models.UniqueConstraint(fields=["assessment", "student"], name="uniq_gradeentry_per_assessment_student")
        ]
        indexes = [models.Index(fields=["assessment", "student"])]

    def __str__(self):
        return f"{self.student} - {self.assessment.assessment_type}: {self.score}"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Presente"
        ABSENT = "absent", "Falta"
        EXCUSED = "excused", "Justificada"

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        limit_choices_to={"role": "student"},
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="attendance_records")
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_markings",
        limit_choices_to={"role": "teacher"},
    )
    date = models.DateField()
    term = models.CharField(max_length=20, choices=Grade.Term.choices, default=Grade.Term.BIMESTER_1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "subject", "date"], name="uniq_attendance_per_day")
        ]
        indexes = [models.Index(fields=["classroom", "date"]), models.Index(fields=["student", "date"])]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"


class AcademicEvent(models.Model):
    class EventType(models.TextChoices):
        CLASS = "class", "Aula"
        EXAM = "exam", "Prova"
        DEADLINE = "deadline", "Entrega"
        MEETING = "meeting", "Reuniao"
        NOTICE = "notice", "Aviso"

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, related_name="events", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.CLASS)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["starts_at", "title"]
        indexes = [models.Index(fields=["classroom", "starts_at"]), models.Index(fields=["subject", "starts_at"])]

    def clean(self):
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("O evento precisa terminar depois de comecar.")

    def __str__(self):
        return self.title


class WeeklySchedule(models.Model):
    class EntryType(models.TextChoices):
        CLASS = "class", "Aula"
        BREAK = "break", "Intervalo"

    class Weekday(models.TextChoices):
        MONDAY = "monday", "Segunda"
        TUESDAY = "tuesday", "Terca"
        WEDNESDAY = "wednesday", "Quarta"
        THURSDAY = "thursday", "Quinta"
        FRIDAY = "friday", "Sexta"
        SATURDAY = "saturday", "Sabado"

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="weekly_schedules")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="weekly_schedules", null=True, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_schedules",
        limit_choices_to={"role": "teacher"},
        null=True,
        blank=True,
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, default=EntryType.CLASS)
    weekday = models.CharField(max_length=20, choices=Weekday.choices)
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    room_label = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["classroom", "weekday", "starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "weekday", "starts_at"],
                name="uniq_schedule_slot_per_classroom",
            ),
        ]
        indexes = [
            models.Index(fields=["classroom", "weekday"]),
            models.Index(fields=["teacher", "weekday"]),
        ]

    def clean(self):
        if self.ends_at <= self.starts_at:
            raise ValidationError("O horario final precisa ser maior que o inicial.")

        overlapping = WeeklySchedule.objects.filter(
            classroom=self.classroom,
            weekday=self.weekday,
            starts_at__lt=self.ends_at,
            ends_at__gt=self.starts_at,
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("Ja existe outra entrada agendada nesse horario para a turma.")

        if self.entry_type == self.EntryType.BREAK:
            if self.subject_id or self.teacher_id:
                raise ValidationError("Intervalo nao pode possuir disciplina ou professor.")
            return

        if not self.subject_id or not self.teacher_id:
            raise ValidationError("Aula precisa ter disciplina e professor.")

        teacher_overlaps = WeeklySchedule.objects.filter(
            teacher=self.teacher,
            weekday=self.weekday,
            starts_at__lt=self.ends_at,
            ends_at__gt=self.starts_at,
            entry_type=self.EntryType.CLASS,
        ).exclude(pk=self.pk)
        if teacher_overlaps.exists():
            raise ValidationError("Professor ja possui aula em outra turma nesse horario.")

        interval_overlaps = WeeklySchedule.objects.filter(
            classroom=self.classroom,
            weekday=self.weekday,
            starts_at__lt=self.ends_at,
            ends_at__gt=self.starts_at,
            entry_type=self.EntryType.BREAK,
        ).exclude(pk=self.pk)
        if interval_overlaps.exists():
            raise ValidationError("Nao e permitido agendar aula durante o intervalo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.classroom} - {self.get_weekday_display()} {self.starts_at}"
