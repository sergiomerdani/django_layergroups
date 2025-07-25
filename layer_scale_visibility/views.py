import requests
import xml.etree.ElementTree as ET
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
    base         = GEOSERVER_URL
    auth         = (GEOSERVER_USER, GEOSERVER_PASS)
    headers_json = {"Accept": "application/json"}
    headers_sld  = {"Accept": "application/vnd.ogc.sld+xml"}

    try:
        # 1) List all layers
        resp = requests.get(f"{base}/layers", auth=auth, headers=headers_json)
        resp.raise_for_status()
        data = resp.json()["layers"]["layer"]
        entries = data if isinstance(data, list) else [data]

        result = []
        ns = {'sld': 'http://www.opengis.net/sld'}

        for entry in entries:
            name        = entry["name"]
            min_scale   = None
            max_scale   = None

            # 2) Get defaultStyle name
            resp2 = requests.get(f"{base}/layers/{name}.json", auth=auth, headers=headers_json)
            resp2.raise_for_status()
            layer_detail = resp2.json()["layer"]
            style_full   = layer_detail.get("defaultStyle", {}).get("name")

            if style_full:
                # Extract local style name (after workspace:)
                style_local = style_full.split(":", 1)[-1]
                sld_url     = f"{base}/workspaces/{workspace}/styles/{style_local}.sld"

                try:
                    # 3) Fetch the full SLD and parse all Rule elements
                    resp3 = requests.get(sld_url, auth=auth, headers=headers_sld)
                    resp3.raise_for_status()
                    root  = ET.fromstring(resp3.content)

                    # 4) Collect every Min/MaxScaleDenominator
                    min_values = []
                    max_values = []
                    for rule in root.findall('.//sld:Rule', ns):
                        min_el = rule.find('sld:MinScaleDenominator', ns)
                        max_el = rule.find('sld:MaxScaleDenominator', ns)
                        if min_el is not None:
                            try:
                                min_values.append(float(min_el.text))
                            except ValueError:
                                pass
                        if max_el is not None:
                            try:
                                max_values.append(float(max_el.text))
                            except ValueError:
                                pass

                    # 5) Compute global min and max if any were found
                    if min_values:
                        min_scale = min(min_values)
                    if max_values:
                        max_scale = max(max_values)

                except requests.RequestException:
                    # on fetch error, leave min_scale/max_scale as None
                    pass

            result.append({
                "name": name,
                "style": style_full,
                "MinScaleDenominator": min_scale,
                "MaxScaleDenominator": max_scale
            })

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