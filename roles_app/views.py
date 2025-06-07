from rest_framework.decorators import api_view
from rest_framework.response    import Response
from rest_framework             import status
import requests

GEOSERVER_URL   = "http://localhost:8080/geoserver"
GEOSERVER_AUTH  = ("admin", "geoserver")

# JSON headers for create / list / update
GS_HEADERS_JSON = {
    "Content-Type": "application/json",
    "Accept":       "application/json"
}


@api_view(["GET", "POST"])
def geoserver_roles(request):
    """
    GET  /api/roles/   → List all roles
    POST /api/roles/   → Create a new role (optionally with parentID and users)
    """
    # ─── 1) LIST ALL ROLES ──────────────────────────────────────────────────
    if request.method == "GET":
        url  = f"{GEOSERVER_URL}/rest/security/roles.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)

    # ─── 2) CREATE A NEW ROLE (only roleName + parentID) ────────────────────
    if request.method == "POST":
        rolename  = request.data.get("roleName")

        if not rolename:
            return Response(
                {"error": "Missing required field 'roleName'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build minimal JSON payload: only roleName and (optional) parentID
        payload = {
            "role": {
                "roleName": rolename,
            }
        }

        create_url = f"{GEOSERVER_URL}/rest/security/roles/role/{rolename}.json"
        resp = requests.post(
            create_url,
            json=payload,
            auth=GEOSERVER_AUTH,
            headers=GS_HEADERS_JSON
        )

        if resp.status_code in (200, 201):
            return Response(
                {"message": f"Role '{rolename}' created successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response({"error": resp.text}, status=resp.status_code)


@api_view(["GET","POST","PUT", "DELETE"])
def geoserver_role_detail(request, rolename):

    base_url = f"{GEOSERVER_URL}/rest/security/roles/role/{rolename}"

    # ─── 1) GET ROLE DETAILS ────────────────────────────────────────────────
    if request.method == "GET":
        url  = f"{base_url}.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)
    
    # ─── POST: Associate USER or GROUP with this role ────────────────────────
    if request.method == "POST":
        username  = request.data.get("username")
        groupname = request.data.get("groupname")

        # ensure exactly one of them is provided
        if bool(username) == bool(groupname):
            return Response(
                {"error": "Provide exactly one of 'username' or 'groupname'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if username:
            # add user to role
            target_url = f"{base_url}/user/{username}"
            success_msg = f"User '{username}' added to role '{rolename}'."
        else:
            # add group to role
            target_url = f"{base_url}/group/{groupname}"
            success_msg = f"Group '{groupname}' added to role '{rolename}'."

        resp = requests.post(target_url, auth=GEOSERVER_AUTH, headers={"Content-Type": "text/plain"})
        if resp.status_code in (200, 201):
            return Response({"message": success_msg}, status=status.HTTP_200_OK)
        return Response({"error": resp.text}, status=resp.status_code)
    
    # ─── PUT: Disassociate a USER or GROUP from this role ─────────────────────
    if request.method == "PUT":
        username  = request.data.get("username")
        groupname = request.data.get("groupname")

        # ensure exactly one provided
        if bool(username) == bool(groupname):
            return Response(
                {"error": "Provide exactly one of 'username' or 'groupname' for removal."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if username:
            # remove user from role
            target_url = f"{base_url}/user/{username}"
            success_msg = f"User '{username}' removed from role '{rolename}'."
        else:
            # remove group from role
            target_url = f"{base_url}/group/{groupname}"
            success_msg = f"Group '{groupname}' removed from role '{rolename}'."

        # GeoServer expects DELETE to that endpoint
        resp = requests.delete(target_url, auth=GEOSERVER_AUTH)
        if resp.status_code in (200, 204):
            return Response({"message": success_msg}, status=status.HTTP_200_OK)
        return Response({"error": resp.text}, status=resp.status_code)


    # ─── 3) DELETE ROLE ─────────────────────────────────────────────────────
    if request.method == "DELETE":
        delete_url = f"{base_url}.json"
        resp = requests.delete(delete_url, auth=GEOSERVER_AUTH)
        if resp.status_code in (200, 204):
            return Response(
                {"message": f"Role '{rolename}' deleted successfully."},
                status=status.HTTP_200_OK
            )
        return Response({"error": resp.text}, status=resp.status_code)

