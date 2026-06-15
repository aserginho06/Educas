from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrTeacher, IsStudent
from academics.permissions import CanAccessClassroomObject
from academics.services import scoped_classrooms, teacher_has_subject_access
from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    search_fields = ("title", "description")
    ordering_fields = ("due_at", "created_at")
    filterset_fields = ("classroom", "subject")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsAdminOrTeacher(), CanAccessClassroomObject()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        queryset = Assignment.objects.select_related("classroom", "subject", "author").filter(
            classroom__in=scoped_classrooms(self.request.user)
        )
        for assignment in queryset:
            assignment.close_if_expired()
        return queryset

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        subject = serializer.validated_data["subject"]
        if self.request.user.role == "teacher" and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode criar atividades nas disciplinas vinculadas.")
        serializer.save(author=self.request.user)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    ordering_fields = ("submitted_at", "reviewed_at", "score")
    filterset_fields = ("assignment", "status")

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsStudent(), CanAccessClassroomObject()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        queryset = Submission.objects.select_related("assignment", "student", "reviewed_by", "assignment__classroom")
        for submission in queryset:
            submission.assignment.close_if_expired()
        user = self.request.user
        if user.role == "student":
            return queryset.filter(student=user, assignment__classroom__in=scoped_classrooms(user))
        return queryset.filter(assignment__classroom__in=scoped_classrooms(user))

    def perform_create(self, serializer):
        assignment = serializer.validated_data["assignment"]
        assignment.close_if_expired()
        if assignment.status == Assignment.Status.CLOSED:
            raise PermissionDenied("Atividade encerrada. Envio bloqueado.")
        status = Submission.Status.LATE if assignment.due_at < timezone.now() else Submission.Status.SUBMITTED
        serializer.save(student=self.request.user, submitted_at=timezone.now(), status=status)
