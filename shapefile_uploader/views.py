import os
import tempfile
import zipfile
import shutil
import subprocess

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from osgeo import ogr

@csrf_exempt
def upload_shapefile(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    shp_zip    = request.FILES.get('shp_zip')
    layer_name = request.POST.get('layer_name')
    if not shp_zip or not layer_name:
        return JsonResponse({'error': 'Missing file or layer name'}, status=400)

    # 1) Save & unzip
    tmp_dir  = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, shp_zip.name)
    with open(zip_path, 'wb') as f:
        for chunk in shp_zip.chunks():
            f.write(chunk)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmp_dir)

    # 2) Locate .shp
    shp_file = next(
        (os.path.join(tmp_dir, fn)
            for fn in os.listdir(tmp_dir)
            if fn.lower().endswith('.shp')),
        None
    )
    if not shp_file:
        return JsonResponse({'error': 'No .shp found in upload'}, status=400)

    # 3) Build PostGIS DSN
    pg = settings.DATABASES['default']
    conn_str = (
        f"PG:dbname={pg['NAME']} "
        f"host={pg['HOST']} "
        f"port={pg['PORT']} "
        f"user={pg['USER']} "
        f"password={pg['PASSWORD']}"
    )

    # 4) Try ogr2ogr CLI first (with PROMOTE_TO_MULTI)
    ogr2ogr_exe = shutil.which("ogr2ogr")
    if ogr2ogr_exe:
        cmd = [
            ogr2ogr_exe,
            "-f", "PostgreSQL",
            conn_str,
            shp_file,
            "-nln", layer_name,
            "-nlt", "PROMOTE_TO_MULTI",       # ← handle your MultiLineString
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=gid",
            "-overwrite",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return JsonResponse({
                "error": "ogr2ogr CLI failed",
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }, status=500)
    else:
        # 5) Fallback: GDAL Python API
        try:
            src_ds    = ogr.Open(shp_file)
            src_layer = src_ds.GetLayer()
            dst_ds    = ogr.Open(conn_str, update=1)
            dst_ds.CopyLayer(src_layer, layer_name)
            src_ds.Destroy()
            dst_ds.Destroy()
        except Exception as e:
            return JsonResponse({
                "error": "GDAL Python API import failed",
                "details": str(e)
            }, status=500)

    # 6) Publish to GeoServer REST (unchanged)
    gs   = settings.GEOSERVER_URL.rstrip('/')
    auth = (settings.GEOSERVER_USER, settings.GEOSERVER_PASS)
    ws    = "roles_test"
    store = "postgres"

    # a) Ensure datastore exists
    ds_url = f"{gs}/rest/workspaces/{ws}/datastores/{store}.xml"
    r = requests.get(ds_url, auth=auth)
    if r.status_code == 404:
        payload = f"""
        <dataStore>
          <name>{store}</name>
          <connectionParameters>
            <host>{pg['HOST']}</host>
            <port>{pg['PORT']}</port>
            <database>{pg['NAME']}</database>
            <user>{pg['USER']}</user>
            <passwd>{pg['PASSWORD']}</passwd>
            <dbtype>postgis</dbtype>
          </connectionParameters>
        </dataStore>
        """
        r = requests.put(ds_url, auth=auth,
                         headers={"Content-Type": "text/xml"},
                         data=payload)
        if not r.ok:
            return JsonResponse({
                "error": "Could not create GeoServer datastore",
                "details": r.text
            }, status=500)

    # b) Publish featureType
    ft_url = f"{gs}/rest/workspaces/{ws}/datastores/{store}/featuretypes"
    ft_payload = f"""
    <featureType>
      <name>{layer_name}</name>
      <nativeName>{layer_name}</nativeName>
      <title>{layer_name}</title>
      <srs>EPSG:3857</srs>
    </featureType>
    """
    r = requests.post(ft_url, auth=auth,
                      headers={"Content-Type": "text/xml"},
                      data=ft_payload)
    if not r.ok:
        return JsonResponse({
            "error": "GeoServer publish failed",
            "details": r.text
        }, status=500)

    # c) Recalculate bounds
    bbox_url = (
        f"{gs}/rest/workspaces/{ws}/datastores/{store}/"
        f"featuretypes/{layer_name}.xml"
        "?recalculate=nativebbox,latlonbbox"
    )
    r = requests.put(bbox_url, auth=auth)
    if not r.ok:
        return JsonResponse({
            "warning": "Layer published but bbox recalc failed",
            "details": r.text
        }, status=202)

    return JsonResponse({"success": True, "layer": layer_name})
