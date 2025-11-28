"""
Proxy views for Yandex Maps APIs to avoid CORS issues
"""

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings


@require_GET
def suggest_proxy(request):
    """Proxy requests to Yandex Suggest API"""
    text = request.GET.get("text", "")

    if not text or len(text) < 2:
        return JsonResponse({"results": []})

    api_key = getattr(settings, "YANDEX_MAPS_GEO_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "API key not configured"}, status=500)

    try:
        url = "https://suggest-maps.yandex.ru/v1/suggest"
        params = {"apikey": api_key, "text": text, "results": 7}

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse(
                {"error": f"Yandex API error: {response.status_code}"},
                status=response.status_code,
            )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def geocode_proxy(request):
    """Proxy requests to Yandex Geocoder API"""
    geocode = request.GET.get("geocode", "")

    if not geocode or len(geocode) < 2:
        return JsonResponse({"error": "geocode parameter required"}, status=400)

    api_key = getattr(settings, "YANDEX_MAPS_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "API key not configured"}, status=500)

    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {"apikey": api_key, "geocode": geocode, "format": "json", "results": 1}

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse(
                {"error": f"Yandex API error: {response.status_code}"},
                status=response.status_code,
            )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
