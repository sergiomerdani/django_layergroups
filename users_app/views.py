from rest_framework.decorators import api_view
from rest_framework.response    import Response
from rest_framework             import status
import requests

GEOSERVER_URL  = "http://localhost:8080/geoserver"
GEOSERVER_AUTH = ("admin", "geoserver")
GS_HEADERS_XML  = {"Content-Type": "application/xml", "Accept": "application/xml"}
GS_HEADERS_JSON = {"Accept": "application/json"}

@api_view(["GET", "POST"])
def geoserver_users(request):
    # — LIST or DETAIL
    if request.method == "GET":
        # list all
        url  = f"{GEOSERVER_URL}/rest/security/usergroup/users.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)

    # — CREATE
    if request.method == "POST":
        username = request.data.get("username")
        password = request.data.get("password")
        enabled  = request.data.get("enabled", "true").lower()
        if not username or not password:
            return Response(
                {"error": "Missing 'username' or 'password'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        xml = f"""
        <user>
          <userName>{username}</userName>
          <password>{password}</password>
          <enabled>{enabled}</enabled>
        </user>
        """.strip()
        url  = f"{GEOSERVER_URL}/rest/security/usergroup/users"
        resp = requests.post(url, data=xml, auth=GEOSERVER_AUTH, headers=GS_HEADERS_XML)
        if resp.status_code == 201:
            return Response({"message": f"User '{username}' created."},
                            status=status.HTTP_201_CREATED)
        return Response({"error": resp.text}, status=resp.status_code)

@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, username):
    """
    GET    /api/users/<username>/ → Retrieve user details (emulated; GeoServer only provides list)
    PUT    /api/users/<username>/ → Update password and/or enabled flag
    DELETE /api/users/<username>/ → Remove a user
    """
    base_url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}"

    # —— GET USER DETAILS ——  
    if request.method == 'GET':
        try:
            # GeoServer does not offer a direct GET for single user; this is just a stub
            return Response(
                {"error": "GeoServer does not support GET user detail. Please use list or fetch by filtering."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # —— UPDATE USER ——  
    if request.method == 'PUT':
        try:
            password = request.data.get("password")
            enabled  = request.data.get("enabled")
            if password is None and enabled is None:
                return Response(
                    {"error": "Provide at least one of 'password' or 'enabled' to update."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Build XML payload
            xml_parts = ["<user>"]
            if password is not None:
                xml_parts.append(f"<password>{password}</password>")
            if enabled is not None:
                xml_parts.append(f"<enabled>{str(enabled).lower()}</enabled>")
            xml_parts.append("</user>")
            xml_payload = "".join(xml_parts)

            # GeoServer requires POST to update existing user
            response = requests.post(
                base_url,
                data=xml_payload,
                auth=GEOSERVER_AUTH,
                headers=GS_HEADERS_XML
            )

            if response.status_code in (200, 204):
                return Response(
                    {"message": f"User '{username}' updated successfully."},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": response.text},
                status=response.status_code
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # —— DELETE USER ——  
    if request.method == 'DELETE':
        try:
            response = requests.delete(base_url, auth=GEOSERVER_AUTH)
            if response.status_code in (200, 204):
                return Response(
                    {"message": f"User '{username}' deleted successfully."},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": response.text},
                status=response.status_code
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
# LIST ALL THE GROUPS OF A USER / ADD USER TO A GROUP
@api_view(["GET", "POST", "PUT"])
def user_groups(request, username):
    """
    GET  /api/users/<username>/groups/ → List all GeoServer groups for a given user
    POST /api/users/<username>/groups/ → Add <username> to a group (JSON: {"group": "<groupname>"})
    PUT /api/users/<username>/groups/ → Delete <username> to a group (JSON: {"group": "<groupname>"})
    """
    # ─── GET: List groups ───────────────────────────────────────────────────
    if request.method == "GET":
        url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}/groups.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)

    # ─── POST: Associate user with a group ─────────────────────────────────
    if request.method == "POST":
        groupname = request.data.get("group")
        if not groupname:
            return Response(
                {"error": "Missing required field 'group'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # GeoServer endpoint to add a user to a group:
        # POST /rest/security/usergroup/user/{username}/group/{groupname}
        url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}/group/{groupname}"
        resp = requests.post(url, auth=GEOSERVER_AUTH, headers={"Content-Type": "text/plain"})
        if resp.status_code in (200, 201):
            return Response(
                {"message": f"User '{username}' added to group '{groupname}'."},
                status=status.HTTP_200_OK
            )
        return Response({"error": resp.text}, status=resp.status_code)

        # ─── DELETE: Unassociate user from a group ───────────────────────────────
    if request.method == "PUT":
        groupname = request.data.get("group")
        if not groupname:
            return Response({"error": "Missing 'group'."}, status=status.HTTP_400_BAD_REQUEST)

        url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}/group/{groupname}"
        # Even though client sent PUT, we still call GeoServer with DELETE
        resp = requests.delete(url, auth=GEOSERVER_AUTH)
        if resp.status_code in (200, 204):
            return Response(
                {"message": f"User '{username}' removed from group '{groupname}'."},
                status=status.HTTP_200_OK
            )
        return Response({"error": resp.text}, status=resp.status_code)

@api_view(["GET"])
def geoserver_roles_for_user(request, username):
    """
    GET /api/roles/user/<username>/ → List all GeoServer roles assigned to <username>
    """
    # GeoServer’s REST endpoint for roles by user:
    #   GET /rest/security/roles/users/{username}.json
    url = f"{GEOSERVER_URL}/rest/security/roles/user/{username}.json"
    resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
    if resp.ok:
        return Response(resp.json(), status=resp.status_code)
    return Response({"error": resp.text}, status=resp.status_code)
