from rest_framework import serializers

from .models import AcademicEvent, AcademicYear, Attendance, Classroom, ClassroomSubject, Enrollment, Grade, GradeLevel, Subject, WeeklySchedule


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"


class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = "__all__"


class ClassroomSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    shift_label = serializers.CharField(source="get_shift_display", read_only=True)

    class Meta:
        model = Classroom
        fields = "__all__"
        read_only_fields = ("slug", "access_code", "created_by")


class ClassroomSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassroomSubject
        fields = "__all__"


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = "__all__"
        read_only_fields = ("approved_by", "approved_at", "requested_at")


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"
        read_only_fields = ("recorded_by", "graded_at")


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = ("marked_by",)


class AcademicEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicEvent
        fields = "__all__"
        read_only_fields = ("created_by",)


class WeeklyScheduleSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)
    entry_type_label = serializers.CharField(source="get_entry_type_display", read_only=True)

    class Meta:
        model = WeeklySchedule
        fields = "__all__"
