from django.conf import settings
from django.db import models
from pathlib import Path

from common.validators import validate_upload_file


class Post(models.Model):
    class PostType(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Aviso"
        MATERIAL = "material", "Material"
        DISCUSSION = "discussion", "Discussao"
        EVENT = "event", "Evento"

    classroom = models.ForeignKey("academics.Classroom", on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    subject = models.ForeignKey("academics.Subject", on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    post_type = models.CharField(max_length=20, choices=PostType.choices, default=PostType.DISCUSSION)
    title = models.CharField(max_length=140)
    content = models.TextField()
    attachment = models.FileField(upload_to="posts/", blank=True, null=True, validators=[validate_upload_file])
    is_pinned = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [models.Index(fields=["classroom", "created_at"]), models.Index(fields=["author", "created_at"])]

    def __str__(self):
        return self.title

    @property
    def attachment_extension(self):
        if not self.attachment:
            return ""
        return Path(self.attachment.name).suffix.lower()

    @property
    def attachment_is_image(self):
        return self.attachment_extension in {".png", ".jpg", ".jpeg", ".webp"}

    @property
    def likes_count(self):
        return self.reactions.count()

    @property
    def comments_count(self):
        return self.comments.count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "created_at"])]

    def __str__(self):
        return f"Comentario de {self.author}"


class PostReaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = "like", "Curtir"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_reactions")
    reaction_type = models.CharField(max_length=20, choices=ReactionType.choices, default=ReactionType.LIKE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="uniq_post_user_reaction")]
        indexes = [models.Index(fields=["post", "reaction_type"])]

    def __str__(self):
        return f"{self.user} - {self.reaction_type}"
