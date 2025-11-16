from django.conf import settings


def user_nko(request):
    """
    Context processor that adds user's NKO (if any) to templates as `user_nko`.

    Use in templates: `{% if user_nko %}...{% endif %}`
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    try:
        from nko.models import NKO

        nko = NKO.objects.filter(owner=user).first()
    except Exception:
        nko = None
    return {"user_nko": nko}
