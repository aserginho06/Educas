from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Profile, StudentProfile, TeacherProfile


User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("phone", "bio", "avatar", "birth_date")


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ("registration_code", "guardian_name", "guardian_phone")


class TeacherProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = ("employee_code", "expertise")


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    student_profile = StudentProfileSerializer(read_only=True)
    teacher_profile = TeacherProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "is_verified",
            "profile",
            "student_profile",
            "teacher_profile",
        )


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "password", "is_active", "is_verified")

    def create(self, validated_data):
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        user = User.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserMeUpdateSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    student_profile = StudentProfileSerializer(required=False)
    teacher_profile = TeacherProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "profile", "student_profile", "teacher_profile")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        student_profile_data = validated_data.pop("student_profile", {})
        teacher_profile_data = validated_data.pop("teacher_profile", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        if instance.role == User.Role.STUDENT and student_profile_data:
            student_profile = instance.student_profile
            for attr, value in student_profile_data.items():
                setattr(student_profile, attr, value)
            student_profile.save()

        if instance.role == User.Role.TEACHER and teacher_profile_data:
            teacher_profile = instance.teacher_profile
            for attr, value in teacher_profile_data.items():
                setattr(teacher_profile, attr, value)
            teacher_profile.save()

        return instance
