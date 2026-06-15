from django import forms

from academics.models import Subject
from academics.services import scoped_classrooms, teacher_has_subject_access
from accounts.models import User

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("classroom", "subject", "post_type", "title", "content", "attachment", "is_pinned")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex.: Material da aula de hoje"}),
            "content": forms.Textarea(attrs={"rows": 4, "placeholder": "Escreva o aviso, material ou orientacao."}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        allowed_classrooms = scoped_classrooms(self.user)
        self.fields["classroom"].queryset = allowed_classrooms
        self.fields["subject"].queryset = Subject.objects.filter(classrooms__in=allowed_classrooms).distinct()
        self.fields["is_pinned"].required = False

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and not self.fields["classroom"].queryset.filter(pk=classroom.pk).exists():
            raise forms.ValidationError("Voce nao pode publicar nessa turma.")

        if self.user.role == User.Role.STUDENT:
            raise forms.ValidationError("Aluno nao pode criar publicacoes.")

        if self.user.role == User.Role.TEACHER and subject and classroom:
            if not teacher_has_subject_access(teacher=self.user, classroom=classroom, subject=subject):
                raise forms.ValidationError("Professor so pode publicar nas disciplinas vinculadas.")

        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2, "placeholder": "Escreva seu comentario."}),
        }
