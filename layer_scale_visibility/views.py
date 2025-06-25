import requests
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# ─── GeoServer creds ──────────────────────────────────────────────
GEOSERVER_URL  = "http://localhost:8080/geoserver/rest"
GEOSERVER_USER = "admin"
GEOSERVER_PASS = "geoserver"
workspace = "roles_test" 
# ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
def layer_list_api(request):
    base    = GEOSERVER_URL
    auth    = (GEOSERVER_USER, GEOSERVER_PASS)
    headers = {"Accept": "application/json"}

    try:
        # 1) list all layers
        resp = requests.get(f"{base}/layers", auth=auth, headers=headers)
        resp.raise_for_status()
        data = resp.json()["layers"]["layer"]
        entries = data if isinstance(data, list) else [data]

        result = []
        for entry in entries:
            name = entry["name"]
            # 2) fetch style info
            resp2 = requests.get(f"{base}/layers/{name}.json", auth=auth, headers=headers)
            resp2.raise_for_status()
            layer_detail = resp2.json()["layer"]
            style = layer_detail.get("defaultStyle", {}).get("name")
            result.append({"name": name, "style": style})

        return Response(result)

    except requests.RequestException as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_502_BAD_GATEWAY
        )


@api_view(['GET'])
def style_detail_api(request, style_name):
    """
    Fetches the raw SLD XML for the given style from GeoServer
    and returns it as application/xml.
    """
    url = f"{GEOSERVER_URL}/workspaces/{workspace}/styles/{style_name}.sld"
    try:
        resp = requests.get(
            url,
            auth=(GEOSERVER_USER, GEOSERVER_PASS),
            headers={'Accept': 'application/vnd.ogc.sld+xml'}
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return HttpResponse(
            f"Error fetching style '{style_name}': {e}",
            status=status.HTTP_502_BAD_GATEWAY,
            content_type="text/plain"
        )

    # Build a response that browsers will render as XML, inline
    response = HttpResponse(
        resp.content,
        content_type="application/xml"   # or "text/xml"
    )
    response['Content-Disposition'] = f'inline; filename="{style_name}.sld"'
    return response