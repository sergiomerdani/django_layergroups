import base64
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

# Configure your GeoServer endpoint + credentials
GEOSERVER_URL = "http://localhost:8080/geoserver"
USERNAME = "user_reader"
PASSWORD = "geoserver"

@csrf_exempt
def proxy(request, path):
    """
    Proxies requests from frontend to GeoServer, injecting Basic Auth.
    Example: /geoserver-proxy/test/wms → http://localhost:8080/geoserver/test/wms
    """
    if path.endswith("ows") or path.endswith("ows/"):
        url = f"{GEOSERVER_URL}/ows"
    else:
        url = f"{GEOSERVER_URL}/{path}"


    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    }

    # Forward GET or POST request
    if request.method == "GET":
        r = requests.get(url, headers=headers, params=request.GET, stream=True)
    else:
        r = requests.post(url, headers=headers, params=request.GET, data=request.body, stream=True)

    # Build Django response
    response = HttpResponse(
        r.content,
        status=r.status_code,
        content_type=r.headers.get("Content-Type", "application/octet-stream"),
    )
    return response
