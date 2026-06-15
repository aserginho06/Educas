from django import forms

from .models import AcademicYear, Assessment, Classroom, Grade, GradeLevel, Lesson, Subject
from .services import scoped_classrooms


class ClassroomCreateForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ("name", "academic_year", "grade_level", "shift", "section")
        labels = {
            "name": "Nome da turma",
            "academic_year": "Ano letivo",
            "grade_level": "Serie/Periodo",
            "shift": "Turno",
            "section": "Identificador da turma",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex.: 2EM-A"}),
            "section": forms.TextInput(attrs={"placeholder": "Ex.: A"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(is_active=True)
        self.fields["grade_level"].queryset = GradeLevel.objects.filter(is_active=True)


class ClassroomJoinByCodeForm(forms.Form):
    access_code = forms.CharField(max_length=12, label="Codigo de acesso")

    def clean_access_code(self):
        return self.cleaned_data["access_code"].strip().upper()


class AttendanceRegistryForm(forms.Form):
    classroom = forms.ModelChoiceField(queryset=Classroom.objects.none(), label="Turma")
    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), label="Disciplina")
    date = forms.DateField(label="Data da aula")
    lesson_count = forms.IntegerField(min_value=1, max_value=20, initial=1, label="Aulas ministradas")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        allowed_classrooms = scoped_classrooms(self.user)
        self.fields["classroom"].queryset = allowed_classrooms
        self.fields["subject"].queryset = Subject.objects.filter(classrooms__in=allowed_classrooms).distinct()
        self.fields["date"].widget.attrs.update({"type": "date"})

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            if not classroom.subjects.filter(pk=subject.pk).exists():
                raise forms.ValidationError("A disciplina nao pertence a essa turma.")

        return cleaned_data


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["classroom", "subject", "date", "quantidade_aulas", "conteudo", "atividade"]
        labels = {
            "classroom": "Turma",
            "subject": "Disciplina",
            "date": "Data",
            "quantidade_aulas": "Quantidade de aulas",
            "conteudo": "Conteúdo ministrado",
            "atividade": "Atividade realizada",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "quantidade_aulas": forms.NumberInput(attrs={"min": 1, "max": 6}),
            "conteudo": forms.Textarea(attrs={"rows": 4}),
            "atividade": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if getattr(self.user, "role", None) == "admin":
            self.fields["classroom"].queryset = Classroom.objects.all()
            self.fields["subject"].queryset = Subject.objects.all().distinct()
        else:
            allowed_classrooms = Classroom.objects.filter(classroom_subjects__teacher=self.user).distinct()
            self.fields["classroom"].queryset = allowed_classrooms
            self.fields["subject"].queryset = Subject.objects.filter(classroom_subjects__teacher=self.user).distinct()

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            if not classroom.subjects.filter(pk=subject.pk).exists():
                raise forms.ValidationError("A disciplina nao pertence a essa turma.")
            if self.user and self.user.role != "admin":
                if not classroom.classroom_subjects.filter(teacher=self.user, subject=subject).exists():
                    raise forms.ValidationError("Voce nao tem permissao para registrar esta aula nessa disciplina.")

        return cleaned_data


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            "classroom",
            "subject",
            "assessment_type",
            "date",
            "description",
            "quantidade_aulas",
        ]
        labels = {
            "classroom": "Turma",
            "subject": "Disciplina",
            "assessment_type": "Tipo",
            "date": "Data",
            "description": "Descricao",
            "quantidade_aulas": "Quantidade de aulas",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Ex.: Funcoes Exponenciais e Logaritmos"}),
            "quantidade_aulas": forms.NumberInput(attrs={"min": 1, "max": 10}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        if getattr(self.user, "role", None) == "admin":
            self.fields["classroom"].queryset = Classroom.objects.all()
            self.fields["subject"].queryset = Subject.objects.all().distinct()
        else:
            allowed_classrooms = Classroom.objects.filter(classroom_subjects__teacher=self.user).distinct()
            self.fields["classroom"].queryset = allowed_classrooms
            self.fields["subject"].queryset = Subject.objects.filter(classroom_subjects__teacher=self.user).distinct()

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            if not classroom.subjects.filter(pk=subject.pk).exists():
                raise forms.ValidationError("A disciplina nao pertence a essa turma.")
            if not classroom.classroom_subjects.filter(teacher=self.user, subject=subject).exists():
                raise forms.ValidationError("Voce nao tem permissao para criar avaliacao nessa disciplina.")

        return cleaned_data


class GradeBatchForm(forms.Form):
    classroom = forms.ModelChoiceField(queryset=Classroom.objects.none(), label="Turma")
    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), label="Disciplina")
    assessment_name = forms.CharField(max_length=120, label="Avaliacao")
    term = forms.ChoiceField(choices=Grade.Term.choices, label="Bimestre")
    max_score = forms.DecimalField(max_digits=5, decimal_places=2, initial=10, label="Valor maximo")
    weight = forms.DecimalField(max_digits=4, decimal_places=2, initial=1, label="Peso")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        allowed_classrooms = scoped_classrooms(self.user)
        self.fields["classroom"].queryset = allowed_classrooms
        self.fields["subject"].queryset = Subject.objects.filter(classrooms__in=allowed_classrooms).distinct()

    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        subject = cleaned_data.get("subject")

        if classroom and subject:
            if not classroom.subjects.filter(pk=subject.pk).exists():
                raise forms.ValidationError("A disciplina nao pertence a essa turma.")

        return cleaned_data
