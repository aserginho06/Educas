from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile, StudentProfile, TeacherProfile


User = get_user_model()


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome", required=False)
    email = forms.EmailField(label="E-mail")
    role = forms.ChoiceField(
        choices=(
            (User.Role.STUDENT, "Aluno"),
            (User.Role.TEACHER, "Professor"),
        ),
        label="Perfil",
    )
    phone = forms.CharField(max_length=30, required=False, label="Telefone")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "role", "phone", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ja existe usuario com esse e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            user.profile.phone = self.cleaned_data.get("phone", "")
            user.profile.save(update_fields=["phone"])
        return user


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome", required=False)
    email = forms.EmailField(label="E-mail")
    avatar = forms.ImageField(required=False, label="Foto de perfil")
    guardian_name = forms.CharField(max_length=150, required=False, label="Responsavel")
    guardian_phone = forms.CharField(max_length=30, required=False, label="Telefone do responsavel")
    expertise = forms.CharField(max_length=120, required=False, label="Area de atuacao")

    class Meta:
        model = Profile
        fields = ("phone", "bio", "birth_date", "avatar")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["email"].initial = self.user.email

        if self.user.role == User.Role.STUDENT and hasattr(self.user, "student_profile"):
            self.fields["guardian_name"].initial = self.user.student_profile.guardian_name
            self.fields["guardian_phone"].initial = self.user.student_profile.guardian_phone
        if self.user.role == User.Role.TEACHER and hasattr(self.user, "teacher_profile"):
            self.fields["expertise"].initial = self.user.teacher_profile.expertise

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.exclude(pk=self.user.pk).filter(email=email).exists():
            raise forms.ValidationError("Ja existe usuario com esse e-mail.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]

        if commit:
            self.user.save(update_fields=["first_name", "last_name", "email"])
            profile.user = self.user
            profile.save()

            if self.user.role == User.Role.STUDENT and hasattr(self.user, "student_profile"):
                student_profile = self.user.student_profile
                student_profile.guardian_name = self.cleaned_data.get("guardian_name", "")
                student_profile.guardian_phone = self.cleaned_data.get("guardian_phone", "")
                student_profile.save(update_fields=["guardian_name", "guardian_phone"])

            if self.user.role == User.Role.TEACHER and hasattr(self.user, "teacher_profile"):
                teacher_profile = self.user.teacher_profile
                teacher_profile.expertise = self.cleaned_data.get("expertise", "")
                teacher_profile.save(update_fields=["expertise"])
        return profile
