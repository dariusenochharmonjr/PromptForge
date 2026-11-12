from django import template

register = template.Library()


@register.filter
def body(comment):
    for name in ("text", "content", "body", "message", "comment"):
        value = getattr(comment, name, None)
        if isinstance(value, str) and value:
            return value
    return ""


@register.simple_tag
def comment_liked(comment, user):
    if not getattr(user, "is_authenticated", False):
        return False
    return comment.likes.filter(user=user).exists()