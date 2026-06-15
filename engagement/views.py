from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminOrTeacher
from academics.permissions import CanAccessClassroomObject
from academics.services import scoped_classrooms, teacher_has_subject_access
from .models import Comment, Post, PostReaction
from .serializers import CommentSerializer, PostReactionSerializer, PostSerializer


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    search_fields = ("title", "content")
    ordering_fields = ("created_at", "updated_at")
    filterset_fields = ("classroom", "subject", "post_type", "is_pinned")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsAdminOrTeacher(), CanAccessClassroomObject()]
        return [IsAuthenticated(), CanAccessClassroomObject()]

    def get_queryset(self):
        return Post.objects.select_related("classroom", "author", "subject").filter(
            classroom__in=scoped_classrooms(self.request.user)
        )

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        subject = serializer.validated_data.get("subject")
        if self.request.user.role == "teacher" and subject and not teacher_has_subject_access(
            teacher=self.request.user,
            classroom=classroom,
            subject=subject,
        ):
            raise PermissionDenied("Professor so pode publicar material nas disciplinas vinculadas.")
        serializer.save(author=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, CanAccessClassroomObject]
    search_fields = ("content",)
    ordering_fields = ("created_at",)
    filterset_fields = ("post",)

    def get_queryset(self):
        return Comment.objects.select_related("post", "author", "post__classroom").filter(
            post__classroom__in=scoped_classrooms(self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostReactionViewSet(viewsets.ModelViewSet):
    serializer_class = PostReactionSerializer
    permission_classes = [IsAuthenticated, CanAccessClassroomObject]
    filterset_fields = ("post", "reaction_type")

    def get_queryset(self):
        return PostReaction.objects.select_related("post", "user", "post__classroom").filter(
            post__classroom__in=scoped_classrooms(self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
