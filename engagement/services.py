from .models import PostReaction


REACTION_EMOJI_MAP = {
    PostReaction.ReactionType.LIKE: "&#10084;",
}


def set_post_reaction(*, post, user, reaction_type=PostReaction.ReactionType.LIKE):
    reaction = PostReaction.objects.filter(post=post, user=user).first()
    if reaction and reaction.reaction_type == reaction_type:
        reaction.delete()
        return None
    if reaction:
        reaction.reaction_type = reaction_type
        reaction.save(update_fields=["reaction_type"])
        return reaction.reaction_type
    PostReaction.objects.create(post=post, user=user, reaction_type=reaction_type)
    return reaction_type


def summarize_post_reactions(post, current_user=None):
    total = post.reactions.count()
    users = [reaction.user.full_name or reaction.user.email for reaction in post.reactions.all()]
    current_user_reaction = None
    if current_user:
        current_user_reaction = next(
            (reaction.reaction_type for reaction in post.reactions.all() if reaction.user_id == current_user.id),
            None,
        )

    return {
        "items": [
            {
                "type": PostReaction.ReactionType.LIKE,
                "emoji": REACTION_EMOJI_MAP[PostReaction.ReactionType.LIKE],
                "count": total,
                "users": users,
            }
        ]
        if total
        else [],
        "current_user_reaction": current_user_reaction,
        "total": total,
    }
