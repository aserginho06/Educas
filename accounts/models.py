from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail e obrigatorio.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa de is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa de is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        TEACHER = "teacher", "Professor"
        STUDENT = "student", "Aluno"

    username = None
    first_name = models.CharField("nome", max_length=150)
    last_name = models.CharField("sobrenome", max_length=150, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["first_name", "email"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def role_label(self):
        return self.get_role_display()

    @property
    def avatar_url(self):
        if hasattr(self, "profile") and self.profile.avatar:
            return self.profile.avatar.url
        return ""

    @property
    def academic_average(self):
        if self.role != self.Role.STUDENT:
            return None
        result = self.grades.aggregate(avg_score=Avg("score"))
        return result["avg_score"]

    def __str__(self):
        return self.full_name or self.email


class Student(User):
    class Meta:
        proxy = True
        verbose_name = "aluno"
        verbose_name_plural = "alunos"


class Teacher(User):
    class Meta:
        proxy = True
        verbose_name = "professor"
        verbose_name_plural = "professores"


class Administrator(User):
    class Meta:
        proxy = True
        verbose_name = "administrador"
        verbose_name_plural = "administradores"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user}"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    registration_code = models.CharField(max_length=30, unique=True)
    guardian_name = models.CharField(max_length=150, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Aluno {self.user.full_name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    employee_code = models.CharField(max_length=30, unique=True)
    expertise = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"Professor {self.user.full_name}"
