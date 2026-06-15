from django import forms
from django.utils import timezone

from academics.models import Classroom, Subject
from academics.services import scoped_classrooms, teacher_has_subject_access
from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    due_at = forms.DateTimeField(
        label="Prazo",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Assignment
        fields = ["classroom", "subject", "title", "description", "due_at", "attachment"]
        labels = {
            "classroom": "Turma",
            "subject": "Disciplina",
            "title": "Título",
            "description": "Descrição",
            "attachment": "Anexo",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Descreva a atividade."}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if getattr(self.user, "role", None) == "admin":
            self.fields["classroom"].queryset = Classroom.objects.all()
            self.fields["subject"].queryset = Subject.objects.all().distinct()
        else:
            classrooms = scoped_classrooms(self.user)
            self.fields["classroom"].queryset = classrooms
            self.fields["subject"].queryset = Subject.objects.filter(classrooms__in=classrooms).distinct()

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            if not classroom.subjects.filter(pk=subject.pk).exists():
                raise forms.ValidationError("A disciplina nao pertence a essa turma.")
            if self.user and self.user.role != "admin":
                if not teacher_has_subject_access(teacher=self.user, classroom=classroom, subject=subject):
                    raise forms.ValidationError("Voce so pode criar atividades nas disciplinas vinculadas.")

        return cleaned_data


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["attachment"]
        labels = {
            "attachment": "Arquivo de entrega",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["attachment"].required = True

    def clean(self):
        cleaned_data = super().clean()
        attachment = cleaned_data.get("attachment")
        if not attachment and not self.instance.pk:
            raise forms.ValidationError("Envie um arquivo para concluir a entrega.")
        return cleaned_data
