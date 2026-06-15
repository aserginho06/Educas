from django.contrib.auth.models import Group, Permission
from django.db import transaction

from .models import User


ROLE_GROUPS = {
    User.Role.ADMIN: "Administradores",
    User.Role.TEACHER: "Professores",
    User.Role.STUDENT: "Alunos",
}

ROLE_PERMISSION_MAP = {
    User.Role.ADMIN: "__all__",
    User.Role.TEACHER: {
        "view_user",
        "view_profile",
        "view_studentprofile",
        "view_teacherprofile",
        "view_subject",
        "view_classroom",
        "view_classroomsubject",
        "view_enrollment",
        "view_grade",
        "add_grade",
        "change_grade",
        "view_attendance",
        "add_attendance",
        "change_attendance",
        "view_academicevent",
        "add_academicevent",
        "change_academicevent",
        "view_post",
        "add_post",
        "change_post",
        "view_comment",
        "add_comment",
        "change_comment",
        "view_postreaction",
        "add_postreaction",
        "delete_postreaction",
        "view_assignment",
        "add_assignment",
        "change_assignment",
        "view_submission",
        "change_submission",
    },
    User.Role.STUDENT: {
        "view_subject",
        "view_classroom",
        "view_classroomsubject",
        "view_enrollment",
        "view_grade",
        "view_attendance",
        "view_academicevent",
        "view_post",
        "view_comment",
        "add_comment",
        "view_postreaction",
        "add_postreaction",
        "delete_postreaction",
        "view_assignment",
        "view_submission",
        "add_submission",
        "change_submission",
    },
}


@transaction.atomic
def sync_groups_and_permissions():
    all_permissions = Permission.objects.all()

    for role, group_name in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        expected = ROLE_PERMISSION_MAP[role]

        if expected == "__all__":
            group.permissions.set(all_permissions)
        else:
            group.permissions.set(all_permissions.filter(codename__in=expected))


def sync_user_role_group(user):
    if not user.pk:
        return

    expected_group = ROLE_GROUPS[user.role]
    groups = Group.objects.filter(name__in=ROLE_GROUPS.values())
    user.groups.remove(*groups)
    group = Group.objects.get(name=expected_group)
    user.groups.add(group)
