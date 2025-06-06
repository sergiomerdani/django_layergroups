from rest_framework.decorators import api_view
from rest_framework.response    import Response
from rest_framework             import status
import requests

GEOSERVER_URL   = "http://localhost:8080/geoserver"
GEOSERVER_AUTH  = ("admin", "geoserver")
GS_HEADERS_XML  = {"Content-Type": "application/xml", "Accept": "application/xml"}
GS_HEADERS_JSON = {"Accept": "application/json"}

@api_view(["GET", "POST"])
def geoserver_groups(request):

    # ─── 1) LIST ALL GROUPS (GET) ──────────────────────────────────────────
    if request.method == "GET":
        # Use the JSON‐output URL, or equivalently set Accept: application/json
        url  = f"{GEOSERVER_URL}/rest/security/usergroup/groups.json"
        resp = requests.get(
            url,
            auth=GEOSERVER_AUTH,
            headers={"Accept": "application/json"}
        )
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)

    # ─── 2) CREATE A NEW GROUP (POST) ─────────────────────────────────────
    if request.method == "POST":
        group_name = request.data.get("groupName")

        if not group_name:
            return Response(
                {"error": "Missing required field 'groupName'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build the JSON payload exactly as GeoServer expects (root key = "group")
        body = {
            "group": {
                "groupName": group_name,

            }
        }

        # POST to /rest/usergroup/group/{groupName}.json  (GeoServer returns 200/201 on success)
        url  = f"{GEOSERVER_URL}/rest/security/usergroup/group/{group_name}.json"
        resp = requests.post(
            url,
            json=body,
            auth=GEOSERVER_AUTH,
            headers={"Content-Type": "application/json"}
        )

        if resp.status_code in (200, 201):
            return Response(
                {"message": f"Group '{group_name}' created successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response({"error": resp.text}, status=resp.status_code)
    
@api_view(["GET", "DELETE"])
def geoserver_group_detail(request, groupname):

    base_url = f"{GEOSERVER_URL}/rest/security/usergroup/group/{groupname}"

    # — GET GROUP DETAILS —
    if request.method == "GET":
        url  = f"{base_url}/users.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": "GeoServer does not support GET group detail."}, status=resp.status_code)

    # — DELETE GROUP —
    if request.method == "DELETE":
        resp = requests.delete(base_url, auth=GEOSERVER_AUTH)
        if resp.status_code in (200, 204):
            return Response(
                {"message": f"Group '{groupname}' deleted successfully."},
                status=status.HTTP_200_OK
            )
        return Response({"error": resp.text}, status=resp.status_code)
