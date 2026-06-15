from django.utils import timezone
from rest_framework import serializers

from .models import Assignment, Submission


class AssignmentSerializer(serializers.ModelSerializer):
    is_closed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ("author", "created_at", "updated_at")


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_status = serializers.CharField(source="assignment.status", read_only=True)

    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = ("student", "reviewed_by", "reviewed_at")

    def update(self, instance, validated_data):
        status = validated_data.get("status")
        if status == Submission.Status.SUBMITTED and not instance.submitted_at:
            validated_data["submitted_at"] = timezone.now()
        return super().update(instance, validated_data)
