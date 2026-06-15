from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.validators import validate_upload_file


class Assignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        CLOSED = "closed", "Encerrada"

    classroom = models.ForeignKey("academics.Classroom", on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, related_name="assignments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_created",
        limit_choices_to={"role": "teacher"},
    )
    title = models.CharField(max_length=140)
    description = models.TextField()
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True, validators=[validate_upload_file])
    due_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    closed_at = models.DateTimeField(blank=True, null=True)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "-created_at"]
        indexes = [models.Index(fields=["classroom", "due_at"]), models.Index(fields=["subject", "due_at"])]

    def __str__(self):
        return self.title

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED or self.due_at <= timezone.now()

    @property
    def current_submission_count(self):
        return self.submissions.count()

    def close_if_expired(self):
        if self.status != self.Status.CLOSED and self.due_at <= timezone.now():
            self.status = self.Status.CLOSED
            self.closed_at = self.closed_at or timezone.now()
            self.save(update_fields=["status", "closed_at", "updated_at"])
        return self.status

    def clean(self):
        if self.closed_at and self.status != self.Status.CLOSED:
            raise ValidationError("Atividade encerrada precisa ter status fechado.")


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SUBMITTED = "submitted", "Entregue"
        LATE = "late", "Atrasada"
        REVIEWED = "reviewed", "Corrigida"
        CLOSED = "closed", "Encerrada"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
        limit_choices_to={"role": "student"},
    )
    text_answer = models.TextField(blank=True)
    attachment = models.FileField(upload_to="submissions/", blank=True, null=True, validators=[validate_upload_file])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(blank=True, null=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True)
    observation = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_submissions",
        limit_choices_to={"role": "teacher"},
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["assignment", "student"], name="uniq_assignment_submission")]
        indexes = [models.Index(fields=["assignment", "status"]), models.Index(fields=["student", "status"])]

    def __str__(self):
        return f"{self.student} - {self.assignment}"

    def clean(self):
        self.assignment.close_if_expired()
        if self.assignment.status == Assignment.Status.CLOSED and self.status not in {self.Status.REVIEWED, self.Status.CLOSED}:
            raise ValidationError("Atividade encerrada nao aceita novas entregas.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_ACTIVITY = "new_activity", "Nova atividade"
        DUE_SOON = "due_soon", "Prazo proximo"
        CORRECTION = "correction", "Correcao realizada"
        COMMENT = "comment", "Comentario"
        GRADE = "grade", "Nota lancada"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_notifications",
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.get_notification_type_display()} para {self.user}"
