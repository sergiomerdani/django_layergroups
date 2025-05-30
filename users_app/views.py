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
        user = request.query_params.get("username")
        if user:
            # retrieve single
            url  = f"{GEOSERVER_URL}/rest/security/usergroup/service/default/user/{user}.json"
        else:
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
        # ——— DELETE ———
    elif request.method == "DELETE":
        username = request.data.get("username")
        if not username:
            return Response(
                {"error": "Username is required in request body"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}"
        response = requests.delete(url, auth=GEOSERVER_AUTH)
        
        if response.status_code in (200, 204):
            return Response(
                {"message": f"User '{username}' deleted successfully"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": f"GeoServer error: {response.text}"},
            status=response.status_code
        )

@api_view(['GET', 'DELETE'])
def user_detail(request, username):
    """
    GET: Retrieve user details
    DELETE: Remove a user
    Works with: /api/users/<username>/
    """
    
    # —— GET USER DETAILS ——
    if request.method == 'GET':
        try:
            url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}"
            response = requests.get(url, auth=GEOSERVER_AUTH)
            
            if response.status_code == 200:
                return Response(response.json())
            return Response(
                {"error": "GeoServer doesn't provide user details via API. You can only delete users."}, 
                status=status.HTTP_404_NOT_FOUND
            )
                
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # —— DELETE USER ——
    elif request.method == 'DELETE':
        try:
            url = f"{GEOSERVER_URL}/rest/security/usergroup/user/{username}"
            response = requests.delete(url, auth=GEOSERVER_AUTH)
            
            if response.status_code in (200, 204):
                return Response(
                    {"message": f"User '{username}' deleted successfully"},
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