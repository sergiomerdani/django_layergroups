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

    # ─── 2) CREATE A NEW ROLE ───────────────────────────────────────────────
    # Expect JSON like:
    # {
    #   "roleName": "my_new_role",
    #   "description": "Optional text",
    #   "users": ["alice", "bob"],        # optional
    #   "parentID": "role_editor"         # optional
    # }
    # ─── 2) CREATE A NEW ROLE (only roleName + parentID) ────────────────────
    if request.method == "POST":
        rolename  = request.data.get("roleName")
        parent_id = request.data.get("parentID", None)

        if not rolename:
            return Response(
                {"error": "Missing required field 'roleName'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build minimal JSON payload: only roleName and (optional) parentID
        payload = {
            "role": {
                "roleName": rolename,
                **({"parentID": parent_id} if parent_id else {})
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


@api_view(["GET", "PUT", "DELETE"])
def geoserver_role_detail(request, rolename):
    """
    GET    /api/roles/<rolename>/   → Retrieve single role (JSON)
    PUT    /api/roles/<rolename>/   → Update description, users, and/or parentID
    DELETE /api/roles/<rolename>/   → Delete a role
    """
    base_url = f"{GEOSERVER_URL}/rest/security/roles/role/{rolename}"

    # ─── 1) GET ROLE DETAILS ────────────────────────────────────────────────
    if request.method == "GET":
        url  = f"{base_url}.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": resp.text}, status=resp.status_code)

    # ─── 2) UPDATE ROLE (description, users, and/or parentID) ─────────────
    if request.method == "PUT":
        description = request.data.get("description", None)
        users       = request.data.get("users", None)       # new list of usernames
        parent_id   = request.data.get("parentID", None)    # new parent role or None

        if description is None and users is None and parent_id is None:
            return Response(
                {"error": "Provide at least one of 'description', 'users', or 'parentID'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build JSON payload under "role" for GeoServer’s update:
        # {
        #   "role": {
        #     "description": "...",              # optional
        #     "userRefs": { "userRef": [...] },  # optional
        #     "parentID": "role_editor"          # optional
        #   }
        # }
        payload = {"role": {}}
        if description is not None:
            payload["role"]["description"] = description
        if users is not None:
            payload["role"]["userRefs"] = {"userRef": users}
        if parent_id is not None:
            payload["role"]["parentID"] = parent_id

        # GeoServer requires PUT to /rest/security/roles/role/{rolename}.json to modify
        update_url = f"{base_url}.json"
        resp = requests.put(
            update_url,
            json=payload,
            auth=GEOSERVER_AUTH,
            headers=GS_HEADERS_JSON
        )

        if resp.status_code in (200, 204):
            changes = []
            if description is not None:
                changes.append("description updated")
            if users is not None:
                changes.append(f"users set to {users}")
            if parent_id is not None:
                changes.append(f"parentID set to '{parent_id}'")
            return Response(
                {"message": f"Role '{rolename}' updated ({', '.join(changes)})."},
                status=status.HTTP_200_OK
            )
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
