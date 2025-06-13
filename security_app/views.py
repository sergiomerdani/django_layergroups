from rest_framework.decorators import api_view
from rest_framework.response    import Response
from rest_framework             import status
import requests

# assume in settings.py you have
GEOSERVER_URL = 'http://localhost:8080/geoserver'
GEOSERVER_USER = 'admin'
GEOSERVER_PASS = 'geoserver'
GS_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

@api_view(['GET', 'PUT'])
def geoserver_masterpw(request):
    """
    GET /api/geoserver/masterpw/    → fetch current master password
    PUT /api/geoserver/masterpw/    → change master password
    JSON body: {
        "oldMasterPassword": "...",
        "newMasterPassword": "..."
    }
    """
    # NOTE: use the `.json` suffix so GeoServer speaks JSON to us
    url = f"{GEOSERVER_URL}/rest/security/masterpw.json"
    # always ask for JSON back
    headers = {'Accept': 'application/json'}

    if request.method == 'GET':
        resp = requests.get(
            url,
            auth=(GEOSERVER_USER, GEOSERVER_PASS),
            headers=headers
        )
        if resp.status_code == 200:
            return Response(resp.json(), status=status.HTTP_200_OK)
        return Response({'error': resp.text}, status=resp.status_code)

    # PUT: update the master password
    payload = {
        'oldMasterPassword': request.data.get('oldMasterPassword'),
        'newMasterPassword': request.data.get('newMasterPassword'),
    }
    if not payload['oldMasterPassword'] or not payload['newMasterPassword']:
        return Response(
            {'error': "Both 'oldMasterPassword' and 'newMasterPassword' are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # tell requests to send JSON
    headers['Content-Type'] = 'application/json'
    resp = requests.put(
        url,
        auth=(GEOSERVER_USER, GEOSERVER_PASS),
        headers=headers,
        json=payload
    )

    if resp.status_code == 200:
        return Response(
            {'message': 'Master password updated successfully.'},
            status=status.HTTP_200_OK
        )
    # GeoServer may return 405 (no perms) or 422 (wrong old pwd / policy failure)
    return Response({'error': resp.text}, status=resp.status_code)



@api_view(['GET', 'PUT'])
def geoserver_self_password(request):
    """
    GET  /api/geoserver/self/password/  
      → proxies GET (usually 405 Method Not Allowed)

    PUT  /api/geoserver/self/password/  
      Body JSON: {
        "oldPassword":     "<current-pw>",
        "newPassword":     "<desired-new-pw>"
      }
      → proxies PUT, validates the old password, and then triggers a reload
    """
    url     = f"{GEOSERVER_URL}/rest/security/self/password"
    headers = {'Accept': 'application/json'}

    # ─── GET branch ─────────────────────────────────────────────────────────
    if request.method == 'GET':
        resp = requests.get(
            url,
            auth=(GEOSERVER_USER, GEOSERVER_PASS),
            headers=headers
        )
        # 401 from GeoServer → custom message
        if resp.status_code == 401:
            return Response(
                {'error': 'Please check username or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        # 200 → return JSON or raw text
        if resp.status_code == 200:
            try:
                return Response(resp.json(), status=200)
            except ValueError:
                return Response({'response': resp.text}, status=200)
        # other errors → bubble up
        return Response({'error': resp.text}, status=resp.status_code)

    # ─── PUT branch ─────────────────────────────────────────────────────────
    old_pw = request.data.get('oldPassword')
    new_pw = request.data.get('newPassword')

    # 1) require both old and new
    if not old_pw or not new_pw:
        return Response(
            {'error': "Both 'oldPassword' and 'newPassword' are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) attempt to change, authenticating with the old password
    headers['Content-Type'] = 'application/json'
    resp = requests.put(
        url,
        auth=(GEOSERVER_USER, old_pw),
        headers=headers,
        json={'newPassword': new_pw}
    )

    # 3) wrong old password?
    if resp.status_code == 401:
        return Response(
            {'error': 'Please check username or existing password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # 4) on success, trigger a config reload so REST auth picks up the new pw
    if resp.status_code == 200:
        reload_resp = requests.post(
            f"{GEOSERVER_URL}/rest/reload",
            auth=(GEOSERVER_USER, old_pw)
        )
        if reload_resp.status_code in (200, 204):
            return Response(
                {'message': 'Password changed and GeoServer reloaded.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'message': 'Password changed, but reload failed.',
                    'reload_error': reload_resp.text
                },
                status=status.HTTP_200_OK
            )

    # 5) any other GeoServer error → pass it along
    return Response({'error': resp.text}, status=resp.status_code)



@api_view(['GET', 'POST', 'PUT'])
def geoserver_acl_layers(request):
    """
    GET  → list rules
    POST → add new rule(s)
    PUT  → merge & update existing rule(s)
    """
    url  = f"{GEOSERVER_URL}/rest/security/acl/layers"
    auth = (GEOSERVER_USER, GEOSERVER_PASS)

    # ─── GET ──────────────────────────────────────────────────────────────────
    if request.method == 'GET':
        resp = requests.get(url, auth=auth, headers=GS_HEADERS)
        if resp.ok:
            try:
                return Response(resp.json(), status=resp.status_code)
            except ValueError:
                return Response({'response': resp.text}, status=resp.status_code)
        return Response({'error': resp.text}, status=resp.status_code)

    # ─── POST ─────────────────────────────────────────────────────────────────
    elif request.method == 'POST':
        payload = request.data
        resp = requests.post(url, auth=auth, headers=GS_HEADERS, json=payload)
        if resp.ok:
            # show a friendly message on empty JSON
            try:
                return Response(resp.json(), status=resp.status_code)
            except ValueError:
                return Response({'message': 'Rule successfully created!'}, status=resp.status_code)
        return Response({'error': resp.text}, status=resp.status_code)

    # ─── PUT ──────────────────────────────────────────────────────────────────
    elif request.method == 'PUT':
        # 1) fetch existing
        get_resp = requests.get(url, auth=auth, headers=GS_HEADERS)
        if not get_resp.ok:
            return Response(
                {'error': f"Failed to fetch existing rules: {get_resp.text}"},
                status=get_resp.status_code
            )
        try:
            current_map = get_resp.json()
        except ValueError:
            return Response({'error': 'Could not parse existing rules.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2) merge payload
        data, updated = request.data, []
        if 'rule' in data:
            r = data['rule']
            res, txt = r.get('@resource'), r.get('text')
            if not res or txt is None:
                return Response(
                    {'error': "Both '@resource' and 'text' are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            current_map[res] = txt
            updated = [res]
        else:
            for res, txt in data.items():
                current_map[res] = txt
                updated.append(res)

        # 3) PUT back
        put_resp = requests.put(url, auth=auth, headers=GS_HEADERS, json=current_map)
        if put_resp.ok:
            return Response(
                {'message': f"Successfully updated rule(s): {', '.join(updated)}"},
                status=put_resp.status_code
            )
        return Response({'error': put_resp.text}, status=put_resp.status_code)

    # ─── fallback ──────────────────────────────────────────────────────────────
    return Response(
        {'error': 'Method not allowed.'},
        status=status.HTTP_405_METHOD_NOT_ALLOWED
    )



@api_view(['POST'])
def geoserver_delete_layer_rule(request):
    """
    POST /api/geoserver/acl/layers/delete/
       Body (either):
         { "resource": "<ws>.<layer>.<access>" }
       or flat‐map style:
         { "<ws>.<layer>.<access>": "" }
       → proxies into GeoServer DELETE /rest/security/acl/layers/{resource}.json
    """
    # 1) pull out the resource string
    data = request.data
    if 'resource' in data:
        resource = data['resource']
    elif len(data) == 1:
        # flat‐map style: use the single key
        resource = next(iter(data.keys()))
    else:
        return Response(
            {'error': "Please send { \"resource\": \"ws.layer.access\" } or a single key."},
            status=400
        )

    # 2) call GeoServer
    gs_url = f"{GEOSERVER_URL}/rest/security/acl/layers/{resource}"
    resp = requests.delete(
        gs_url,
        auth=(GEOSERVER_USER, GEOSERVER_PASS),
        headers={'Accept': 'application/json'}
    )

    # 3) forward result
    if resp.status_code in (200, 204):
        return Response(
            {'message': f"Successfully deleted rule '{resource}'."},
            status=resp.status_code
        )
    return Response({'error': resp.text}, status=resp.status_code)
