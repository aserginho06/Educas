from django.contrib import admin

from .models import Assignment, Notification, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "subject", "author", "due_at", "points")
    search_fields = ("title", "classroom__name", "subject__name", "author__email")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "status", "submitted_at", "score")
    list_filter = ("status",)
    search_fields = ("assignment__title", "student__email")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "assignment", "created_at", "is_read")
    list_filter = ("notification_type", "is_read")
    search_fields = ("user__email", "assignment__title", "submission__student__email")
