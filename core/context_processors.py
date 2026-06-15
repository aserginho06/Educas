from assignments.models import Notification


def shell_notifications(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "shell_notifications": [],
            "shell_notifications_unread_count": 0,
        }

    return {
        "shell_notifications": list(
            Notification.objects.filter(user=request.user)
            .select_related("assignment", "submission")
            .order_by("-created_at")[:6]
        ),
        "shell_notifications_unread_count": Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count(),
    }
