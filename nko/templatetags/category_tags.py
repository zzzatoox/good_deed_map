from django import template
from django.utils.text import slugify as dj_slugify

from nko.models import Category

register = template.Library()


@register.simple_tag
def get_categories():
    """Return all categories for use in templates."""
    return Category.objects.all()


@register.filter
def slugify(value):
    """Slugify with unicode support for Cyrillic characters."""
    try:
        return dj_slugify(str(value), allow_unicode=True)
    except Exception:
        return ""
