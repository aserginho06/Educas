from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from .models import Classroom


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.role == User.Role.ADMIN


class CanManageAcademicRecord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {User.Role.ADMIN, User.Role.TEACHER}


class CanAccessClassroomObject(BasePermission):
    def _resolve_classroom(self, obj):
        if isinstance(obj, Classroom):
            return obj
        if hasattr(obj, "classroom"):
            return obj.classroom
        if hasattr(obj, "post") and hasattr(obj.post, "classroom"):
            return obj.post.classroom
        if hasattr(obj, "assignment") and hasattr(obj.assignment, "classroom"):
            return obj.assignment.classroom
        return None

    def has_object_permission(self, request, view, obj):
        classroom = self._resolve_classroom(obj)
        if classroom is None:
            return request.user.role == User.Role.ADMIN
        if request.user.role == User.Role.ADMIN:
            return True
        if request.user.role == User.Role.TEACHER:
            return classroom.classroom_subjects.filter(teacher=request.user).exists() or classroom.homeroom_teacher_id == request.user.id
        return classroom.enrollments.filter(student=request.user, status="approved").exists()
