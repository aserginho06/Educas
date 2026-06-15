from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg, Count, Q

from .models import AcademicEvent, Assessment, Attendance, AttendanceRecord, Classroom, Enrollment, Grade, GradeEntry


User = get_user_model()


def scoped_classrooms(user):
    if user.role == User.Role.ADMIN:
        return Classroom.objects.all()

    if user.role == User.Role.TEACHER:
        return Classroom.objects.filter(
            Q(homeroom_teacher=user) | Q(classroom_subjects__teacher=user)
        ).distinct()

    return Classroom.objects.filter(enrollments__student=user, enrollments__status="approved").distinct()


def enroll_student_with_access_code(*, student, access_code):
    classroom = Classroom.objects.get(access_code=access_code, is_active=True)
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        classroom=classroom,
        defaults={
            "status": Enrollment.Status.APPROVED,
            "approved_at": timezone.now(),
        },
    )
    if not created and enrollment.status != Enrollment.Status.APPROVED:
        enrollment.status = Enrollment.Status.APPROVED
        enrollment.approved_at = timezone.now()
        enrollment.save(update_fields=["status", "approved_at"])
    return enrollment


def teacher_has_subject_access(*, teacher, classroom, subject):
    return classroom.classroom_subjects.filter(teacher=teacher, subject=subject).exists()


def _build_student_subject_summary(entries):
    assessment_map = {}
    for entry in entries:
        subject_name = entry.assessment.subject.name
        assessment_map.setdefault(subject_name, []).append(entry)

    report = []
    for subject_name, entries in assessment_map.items():
        best_scores = {}
        for entry in entries:
            assessment_type = entry.assessment.assessment_type
            current_best = best_scores.get(assessment_type)
            if current_best is None or float(entry.score) > float(current_best):
                best_scores[assessment_type] = entry.score

        def best_of(primary, recovery):
            primary_score = best_scores.get(primary)
            recovery_score = best_scores.get(recovery)
            if primary_score is None and recovery_score is None:
                return None
            if primary_score is None:
                return float(recovery_score)
            if recovery_score is None:
                return float(primary_score)
            return max(float(primary_score), float(recovery_score))

        p1 = best_of(Assessment.AssessmentType.P1, Assessment.AssessmentType.REC1)
        p2 = best_of(Assessment.AssessmentType.P2, Assessment.AssessmentType.REC2)
        p3 = best_of(Assessment.AssessmentType.P3, Assessment.AssessmentType.REC3)
        p4 = best_of(Assessment.AssessmentType.P4, Assessment.AssessmentType.REC4)
        final = best_scores.get(Assessment.AssessmentType.FINAL)

        ms1 = None
        if p1 is not None or p2 is not None:
            values = [v for v in (p1, p2) if v is not None]
            ms1 = round(sum(values) / len(values), 2)

        ms2 = None
        if p3 is not None or p4 is not None:
            values = [v for v in (p3, p4) if v is not None]
            ms2 = round(sum(values) / len(values), 2)

        mf = None
        if ms1 is not None or ms2 is not None:
            values = [v for v in (ms1, ms2) if v is not None]
            mf = round(sum(values) / len(values), 2)

        if final is not None:
            final = float(final)
            mf = final

        status = "Pendente"
        if mf is not None:
            status = "AP" if mf >= 7 else "RE"

        def format_numeric(value):
            return format(value, ".1f") if value is not None else None

        report.append(
            {
                "subject": subject_name,
                "grades": entries,
                "scores": {
                    "P1": format_numeric(p1),
                    "REC1": format_numeric(best_scores.get(Assessment.AssessmentType.REC1)),
                    "P2": format_numeric(p2),
                    "REC2": format_numeric(best_scores.get(Assessment.AssessmentType.REC2)),
                    "P3": format_numeric(p3),
                    "REC3": format_numeric(best_scores.get(Assessment.AssessmentType.REC3)),
                    "P4": format_numeric(p4),
                    "REC4": format_numeric(best_scores.get(Assessment.AssessmentType.REC4)),
                    "FINAL": format_numeric(final),
                },
                "average": format_numeric(mf),
                "terms": {
                    "MS1": format_numeric(ms1),
                    "MS2": format_numeric(ms2),
                    "MF": format_numeric(mf),
                },
                "status": status,
            }
        )
    return report


def student_grade_report(student):
    entries = student.grade_entries.select_related("assessment__subject").order_by("assessment__subject__name", "assessment__date")
    return _build_student_subject_summary(entries)


def student_grade_chart_data(student):
    classrooms = student.enrollments.filter(status=Enrollment.Status.APPROVED).values_list("classroom", flat=True)
    entries = student.grade_entries.select_related("assessment__subject").order_by("assessment__subject__name")
    grouped = {}
    for entry in entries:
        subject_name = entry.assessment.subject.name
        grouped.setdefault(subject_name, []).append(float(entry.score))

    chart_data = []
    for subject_name, scores in grouped.items():
        average = round(sum(scores) / len(scores), 2)
        class_avg = GradeEntry.objects.filter(assessment__subject__name=subject_name, assessment__classroom__in=classrooms).aggregate(avg_score=Avg("score"))["avg_score"]
        class_avg = float(class_avg) if class_avg is not None else 0.0
        chart_data.append({
            "subject": subject_name,
            "student_average": average,
            "class_average": round(class_avg, 2),
        })
    return chart_data


def student_attendance_summary(student):
    records = student.lesson_attendance_records.select_related("lesson")
    total_lessons = sum(record.lesson.quantidade_aulas for record in records)
    absences = sum(record.absences for record in records)
    frequency = 100 if total_lessons == 0 else round(((total_lessons - absences) / total_lessons) * 100, 1)
    return {
        "total": total_lessons,
        "absences": absences,
        "frequency": frequency,
    }


def student_attendance_subject_summary(student):
    summary = {}
    for record in student.lesson_attendance_records.select_related("lesson__subject"):
        subject_name = record.lesson.subject.name
        subject = summary.setdefault(
            subject_name,
            {"present": 0, "absent": 0, "excused": 0, "total": 0, "percentage": 0},
        )
        lesson_hours = record.lesson.quantidade_aulas
        subject["total"] += lesson_hours
        subject["absent"] += record.absences
        subject["present"] += max(lesson_hours - record.absences, 0)

    for subject_name, data in summary.items():
        data["percentage"] = 100 if data["total"] == 0 else round(((data["total"] - data["absent"]) / data["total"]) * 100, 1)
    return summary
