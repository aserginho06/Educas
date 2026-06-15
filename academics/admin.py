from django.contrib import admin

from .models import AcademicEvent, AcademicYear, Attendance, AttendanceRecord, Classroom, ClassroomSubject, Enrollment, Grade, GradeLevel, Lesson, Subject, WeeklySchedule


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "starts_on", "ends_on", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "year")


@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "stage", "sequence", "is_active")
    list_filter = ("stage", "is_active")
    search_fields = ("name", "code")


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "grade_level", "shift", "section", "school_year", "homeroom_teacher", "is_active")
    list_filter = ("school_year", "shift", "is_active")
    search_fields = ("name", "section", "slug")


@admin.register(ClassroomSubject)
class ClassroomSubjectAdmin(admin.ModelAdmin):
    list_display = ("classroom", "subject", "teacher", "weekly_workload")
    search_fields = ("classroom__name", "subject__name", "teacher__email")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "classroom", "status", "requested_at", "approved_by")
    list_filter = ("status",)
    search_fields = ("student__email", "classroom__name")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("student", "classroom", "subject", "term", "assessment_name", "score", "graded_at")
    search_fields = ("student__email", "subject__name", "assessment_name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "classroom", "subject", "term", "date", "status")
    list_filter = ("status", "term", "date")
    search_fields = ("student__email", "subject__name")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "absences", "created_at")
    list_filter = ("lesson__classroom", "lesson__subject")
    search_fields = ("student__email", "lesson__subject__name", "lesson__classroom__name")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("date", "classroom", "subject", "professor", "quantidade_aulas")
    list_filter = ("date", "classroom", "subject", "professor")
    search_fields = ("professor__email", "classroom__name", "subject__name", "conteudo")


@admin.register(AcademicEvent)
class AcademicEventAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "subject", "event_type", "starts_at", "is_published")
    list_filter = ("event_type", "is_published")
    search_fields = ("title", "classroom__name", "subject__name")


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ("classroom", "weekday", "entry_type", "starts_at", "ends_at", "subject", "teacher")
    list_filter = ("weekday", "entry_type", "classroom")
    search_fields = ("classroom__name", "subject__name", "teacher__email")
