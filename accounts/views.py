from django.contrib.auth import get_user_model
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsPlatformAdmin
from .serializers import UserMeUpdateSerializer, UserSerializer, UserWriteSerializer


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile", "student_profile", "teacher_profile").all()
    search_fields = ("email", "first_name", "last_name")
    ordering_fields = ("first_name", "email", "created_at")

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsPlatformAdmin()]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserWriteSerializer
        return UserSerializer

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @me.mapping.patch
    def update_me(self, request):
        serializer = UserMeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
