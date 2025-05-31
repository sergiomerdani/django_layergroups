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
    """
    GET    /api/users/             → list all users
    GET    /api/users/?username=X → retrieve user X
    POST   /api/users/             → create user (JSON: username, password, enabled)
    PUT    /api/users/             → update user (JSON: username, [password], [enabled])
    DELETE /api/users/             → delete user (JSON: username)
    """
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