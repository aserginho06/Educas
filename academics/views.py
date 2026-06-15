from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrTeacher, IsPlatformAdmin
from .models import AcademicEvent, AcademicYear, Attendance, Classroom, ClassroomSubject, Enrollment, Grade, GradeLevel, Subject, WeeklySchedule
from .permissions import CanAccessClassroomObject, CanManageAcademicRecord, IsAdminOrReadOnly
from .serializers import (
    AcademicEventSerializer,
    AcademicYearSerializer,
    AttendanceSerializer,
    ClassroomSerializer,
    ClassroomSubjectSerializer,
    EnrollmentSerializer,
    GradeSerializer,
    GradeLevelSerializer,
    SubjectSerializer,
    WeeklyScheduleSerializer,
)
from .services import scoped_classrooms, teacher_has_subject_access


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ("code", "name")
    ordering_fields = ("name", "code")


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ("name",)
    ordering_fields = ("year", "name")


class GradeLevelViewSet(viewsets.ModelViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ("name", "code", "stage")
    ordering_fields = ("sequence", "name")


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    search_fields = ("name", "slug", "section")
    ordering_fields = ("school_year", "name")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsPlatformAdmin()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        return scoped_classrooms(self.request.user).select_related("homeroom_teacher", "created_by").prefetch_related("subjects")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ClassroomSubjectViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSubjectSerializer
    search_fields = ("classroom__name", "subject__name", "teacher__email")
    ordering_fields = ("classroom__name", "subject__name")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsPlatformAdmin()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        return ClassroomSubject.objects.select_related("classroom", "subject", "teacher").filter(
            classroom__in=scoped_classrooms(self.request.user)
        )


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    search_fields = ("student__email", "classroom__name")
    ordering_fields = ("requested_at", "approved_at")
    filterset_fields = ("status", "classroom")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsPlatformAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Enrollment.objects.select_related("student", "classroom", "approved_by")
        user = self.request.user
        if user.role == "admin":
            return queryset
        if user.role == "teacher":
            return queryset.filter(classroom__in=scoped_classrooms(user))
        return queryset.filter(student=user)

    def perform_update(self, serializer):
        status = serializer.validated_data.get("status")
        approved_at = timezone.now() if status == Enrollment.Status.APPROVED else None
        serializer.save(approved_by=self.request.user, approved_at=approved_at)


class GradeViewSet(viewsets.ModelViewSet):
    serializer_class = GradeSerializer
    search_fields = ("student__email", "subject__name", "assessment_name")
    ordering_fields = ("graded_at", "score")
    filterset_fields = ("classroom", "subject", "student")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), CanManageAcademicRecord(), CanAccessClassroomObject()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        queryset = Grade.objects.select_related("classroom", "student", "subject", "recorded_by")
        user = self.request.user
        if user.role == "student":
            return queryset.filter(student=user, classroom__in=scoped_classrooms(user))
        if user.role == "teacher":
            return queryset.filter(
                classroom__classroom_subjects__teacher=user,
                subject__classroom_subjects__teacher=user,
            ).distinct()
        return queryset.filter(classroom__in=scoped_classrooms(user))

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        subject = serializer.validated_data["subject"]
        if self.request.user.role == "teacher" and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode lancar notas nas disciplinas vinculadas.")
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        classroom = serializer.validated_data.get("classroom", serializer.instance.classroom)
        subject = serializer.validated_data.get("subject", serializer.instance.subject)
        if self.request.user.role == "teacher" and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode editar notas das disciplinas vinculadas.")
        serializer.save()


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    search_fields = ("student__email", "subject__name", "notes")
    ordering_fields = ("date",)
    filterset_fields = ("classroom", "subject", "student", "status")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), CanManageAcademicRecord(), CanAccessClassroomObject()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        queryset = Attendance.objects.select_related("classroom", "student", "subject", "marked_by")
        user = self.request.user
        if user.role == "student":
            return queryset.filter(student=user, classroom__in=scoped_classrooms(user))
        if user.role == "teacher":
            return queryset.filter(
                classroom__classroom_subjects__teacher=user,
                subject__classroom_subjects__teacher=user,
            ).distinct()
        return queryset.filter(classroom__in=scoped_classrooms(user))

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        subject = serializer.validated_data["subject"]
        if self.request.user.role == "teacher" and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode registrar frequencia nas disciplinas vinculadas.")
        serializer.save(marked_by=self.request.user)

    def perform_update(self, serializer):
        classroom = serializer.validated_data.get("classroom", serializer.instance.classroom)
        subject = serializer.validated_data.get("subject", serializer.instance.subject)
        if self.request.user.role == "teacher" and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode editar frequencia das disciplinas vinculadas.")
        serializer.save()


class AcademicEventViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicEventSerializer
    search_fields = ("title", "description")
    ordering_fields = ("starts_at", "title")
    filterset_fields = ("classroom", "subject", "event_type", "is_published")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsAdminOrTeacher()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        return AcademicEvent.objects.select_related("classroom", "subject", "created_by").filter(
            classroom__in=scoped_classrooms(self.request.user)
        ) | AcademicEvent.objects.select_related("classroom", "subject", "created_by").filter(classroom__isnull=True)

    def perform_create(self, serializer):
        classroom = serializer.validated_data.get("classroom")
        subject = serializer.validated_data.get("subject")
        if self.request.user.role == "teacher":
            if classroom is None:
                raise PermissionDenied("Professor so pode criar eventos para as proprias turmas.")
            if not scoped_classrooms(self.request.user).filter(pk=classroom.pk).exists():
                raise PermissionDenied("Professor so pode criar eventos nas proprias turmas.")
            if subject and not teacher_has_subject_access(
                teacher=self.request.user,
                classroom=classroom,
                subject=subject,
            ):
                raise PermissionDenied("Professor so pode criar eventos das disciplinas vinculadas.")
        serializer.save(created_by=self.request.user)


class WeeklyScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = WeeklyScheduleSerializer
    search_fields = ("classroom__name", "subject__name", "teacher__email")
    ordering_fields = ("weekday", "starts_at", "ends_at")
    filterset_fields = ("classroom", "subject", "teacher", "weekday")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsPlatformAdmin()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        return WeeklySchedule.objects.select_related("classroom", "subject", "teacher").filter(
            classroom__in=scoped_classrooms(self.request.user)
        )
