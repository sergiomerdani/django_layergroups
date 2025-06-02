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
        members    = request.data.get("members", [])
        enabled    = request.data.get("enabled")

        if not group_name:
            return Response(
                {"error": "Missing required field 'groupName'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build the JSON payload exactly as GeoServer expects (root key = "group")
        body = {
            "group": {
                "groupName": group_name,
                "enabled": enabled,
                # Only include "users" if member list is nonempty
                **({"users": members} if members else {})
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
    
@api_view(["GET", "PUT", "DELETE"])
def geoserver_group_detail(request, groupname):

    base_url = f"{GEOSERVER_URL}/rest/security/usergroup/group/{groupname}"

    # — GET GROUP DETAILS —
    if request.method == "GET":
        url  = f"{base_url}.json"
        resp = requests.get(url, auth=GEOSERVER_AUTH, headers=GS_HEADERS_JSON)
        if resp.ok:
            return Response(resp.json(), status=resp.status_code)
        return Response({"error": "GeoServer does not support GET group detail. Please use list or fetch by filtering."}, status=resp.status_code)

# ─── PUT: Update either "enabled" or "members" (or both) ──────────────
    if request.method == "PUT":
        enabled = request.data.get("enabled", None)    # true/false or None
        members = request.data.get("members", None)    # list of usernames or None

        # If neither field was provided, error out
        if enabled is None and members is None:
            return Response(
                {"error": "Provide at least one of 'enabled' (boolean) or 'members' (list of usernames)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build the <group>…</group> block, including only the provided subelements:
        xml_lines = ["<group>"]

        # 1) If "enabled" was present, include it:
        if enabled is not None:
            xml_lines.append(f"  <enabled>{str(enabled).lower()}</enabled>")

        # 2) If "members" was present, include a <users>…</users> block:
        if members is not None:
            # We replace the entire member list with exactly what's in "members"
            xml_lines.append("  <users>")
            for username in members:
                xml_lines.append(f"    <user>{username}</user>")
            xml_lines.append("  </users>")

        xml_lines.append("</group>")
        xml_payload = "\n".join(xml_lines)

        # GeoServer expects a POST with XML to the .xml URL to update an existing group
        update_url = f"{base_url}.xml"
        resp = requests.post(
            update_url,
            data=xml_payload,
            auth=GEOSERVER_AUTH,
            headers=GS_HEADERS_XML
        )

        if resp.status_code in (200, 204):
            # Build a success message indicating what changed
            changed = []
            if enabled is not None:
                changed.append(f"enabled={enabled}")
            if members is not None:
                changed.append(f"members={members}")
            return Response(
                {"message": f"Group '{groupname}' updated ({', '.join(changed)})."},
                status=status.HTTP_200_OK
            )

        # If GeoServer returns an error (e.g. malformed XML), forward it
        return Response({"error": resp.text}, status=resp.status_code)

    # — DELETE GROUP —
    if request.method == "DELETE":
        resp = requests.delete(base_url, auth=GEOSERVER_AUTH)
        if resp.status_code in (200, 204):
            return Response(
                {"message": f"Group '{groupname}' deleted successfully."},
                status=status.HTTP_200_OK
            )
        return Response({"error": resp.text}, status=resp.status_code)
