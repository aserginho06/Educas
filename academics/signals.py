from datetime import date

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import AcademicYear, GradeLevel


GRADE_LEVEL_SEED = [
    ("1EF", "1o Ano", GradeLevel.EducationStage.FUNDAMENTAL_I, 1),
    ("2EF", "2o Ano", GradeLevel.EducationStage.FUNDAMENTAL_I, 2),
    ("3EF", "3o Ano", GradeLevel.EducationStage.FUNDAMENTAL_I, 3),
    ("4EF", "4o Ano", GradeLevel.EducationStage.FUNDAMENTAL_I, 4),
    ("5EF", "5o Ano", GradeLevel.EducationStage.FUNDAMENTAL_I, 5),
    ("6EF", "6o Ano", GradeLevel.EducationStage.FUNDAMENTAL_II, 6),
    ("7EF", "7o Ano", GradeLevel.EducationStage.FUNDAMENTAL_II, 7),
    ("8EF", "8o Ano", GradeLevel.EducationStage.FUNDAMENTAL_II, 8),
    ("9EF", "9o Ano", GradeLevel.EducationStage.FUNDAMENTAL_II, 9),
    ("1EM", "1o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 10),
    ("2EM", "2o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 11),
    ("3EM", "3o Ano EM", GradeLevel.EducationStage.HIGH_SCHOOL, 12),
]


@receiver(post_migrate)
def seed_academic_structure(sender, **kwargs):
    if sender.name != "academics":
        return

    current_year = date.today().year
    for year in (current_year, current_year + 1):
        AcademicYear.objects.update_or_create(
            year=year,
            defaults={"name": str(year), "is_active": True},
        )

    for code, name, stage, sequence in GRADE_LEVEL_SEED:
        GradeLevel.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "stage": stage,
                "sequence": sequence,
                "is_active": True,
            },
        )
