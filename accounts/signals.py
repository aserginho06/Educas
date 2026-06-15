from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Profile, StudentProfile, TeacherProfile
from .services import sync_groups_and_permissions, sync_user_role_group


User = get_user_model()


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    sync_groups_and_permissions()
    if sender.name != "accounts":
        return

    admin_defaults = {
        "first_name": "Administrador",
        "last_name": "Educas",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
        "is_verified": True,
    }
    admin_user, created = User.objects.get_or_create(
        email="admin@educas.com",
        defaults=admin_defaults,
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save(update_fields=["password"])


@receiver(post_save, sender=User)
def create_or_update_user_support_data(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
    sync_user_role_group(instance)

    if instance.role == User.Role.STUDENT:
        StudentProfile.objects.get_or_create(
            user=instance,
            defaults={"registration_code": f"ALN-{instance.pk:05d}"},
        )
    elif instance.role == User.Role.TEACHER:
        TeacherProfile.objects.get_or_create(
            user=instance,
            defaults={"employee_code": f"PRF-{instance.pk:05d}"},
        )
