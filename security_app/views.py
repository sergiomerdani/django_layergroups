from rest_framework.decorators import api_view
from rest_framework.response    import Response
from rest_framework             import status
import requests

# assume in settings.py you have
GEOSERVER_URL = 'http://localhost:8080/geoserver'
GEOSERVER_USER = 'user_reader'
GEOSERVER_PASS = 'geoserver'

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
    GET /api/geoserver/self/password/  
    → proxies GET (usually 405)

    PUT /api/geoserver/self/password/  
    Body: { "newPassword": "..." }
    → proxies PUT and then triggers a reload
    """
    url = f"{GEOSERVER_URL}/rest/security/self/password"
    headers = {'Accept': 'application/json'}

    if request.method == 'GET':
        resp = requests.get(url,
                            auth=(GEOSERVER_USER, GEOSERVER_PASS),
                            headers=headers)
        if resp.status_code == 200:
            try:
                return Response(resp.json(), status=200)
            except ValueError:
                return Response({'response': resp.text}, status=200)
        return Response({'error': resp.text}, status=resp.status_code)

    # PUT → change your password
    new_pw = request.data.get('newPassword')
    if not new_pw:
        return Response(
            {'error': "Missing required field 'newPassword'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    headers['Content-Type'] = 'application/json'
    resp = requests.put(url,
                        auth=(GEOSERVER_USER, GEOSERVER_PASS),
                        headers=headers,
                        json={'newPassword': new_pw})

    if resp.status_code == 200:
        # **force a reload** so REST auth picks up the new password immediately
        reload_url = f"{GEOSERVER_URL}/rest/reload"
        reload_resp = requests.post(reload_url,
                                    auth=(GEOSERVER_USER, GEOSERVER_PASS))
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

    return Response({'error': "Please check username or password."}, status=resp.status_code)
