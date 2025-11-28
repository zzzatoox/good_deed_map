from django.conf import settings


def public_settings(request):
    """Expose non-sensitive public settings to templates (e.g. API keys for client-side libs).

    Only include values that are safe to embed in client-side JS (e.g. maps API key).
    """
    return {
        "YANDEX_MAPS_API_KEY": getattr(settings, "YANDEX_MAPS_API_KEY", ""),
        "YANDEX_MAPS_GEO_API_KEY": getattr(settings, "YANDEX_MAPS_GEO_API_KEY", ""),
    }
