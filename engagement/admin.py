from django.contrib import admin

from .models import Comment, Post, PostReaction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "author", "post_type", "is_pinned", "is_published", "created_at")
    list_filter = ("post_type", "is_pinned", "is_published")
    search_fields = ("title", "content", "author__email")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("post__title", "author__email", "content")


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "reaction_type", "created_at")
    search_fields = ("post__title", "user__email")
