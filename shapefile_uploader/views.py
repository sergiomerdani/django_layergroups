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

    # 3) Read source SRS from .prj (with fallback)
    src_ds    = ogr.Open(shp_file)
    src_layer = src_ds.GetLayer()
    srs       = src_layer.GetSpatialRef()
    geom_code = src_layer.GetGeomType()
    geom_type = ogr.GeometryTypeToName(geom_code)
    print(geom_type)
    if srs:
        auth_name = srs.GetAuthorityName(None)
        auth_code = srs.GetAuthorityCode(None)
        srs_code  = f"{auth_name}:{auth_code}" if auth_name and auth_code else srs.ExportToProj4()
    else:
        # no .prj present — choose a sensible default or error out
        srs_code = "EPSG:3857"
    src_ds.Destroy()


    # — map OGR geometry constants to the OGR “-nlt” strings
    if geom_type == "Point":
        nlt = "Point"
    elif geom_type == "Line String":
        nlt = "LineString"
    elif geom_type == "Polygon":
        nlt = "Geometry"
    else:
        nlt = "PROMOTE_TO_MULTI"
    # 4) Build PostGIS DSN
    pg = settings.DATABASES['default']
    conn_str = (
        f"PG:dbname={pg['NAME']} "
        f"host={pg['HOST']} "
        f"port={pg['PORT']} "
        f"user={pg['USER']} "
        f"password={pg['PASSWORD']}"
    )

    print(nlt)
    # 5) Ingest into PostGIS (CLI w/ PROMOTE_TO_MULTI or Python API)
    ogr2ogr_exe = shutil.which("ogr2ogr")
    extra = []
    if geom_type in (ogr.wkbMultiLineString, ogr.wkbMultiPoint, ogr.wkbMultiPolygon):
        extra = ["-explodecollections"]
    if ogr2ogr_exe:
        cmd = [
            ogr2ogr_exe,
            "-f", "PostgreSQL",
            conn_str,
            shp_file,
            "-nln", layer_name,
            "-nlt", nlt,
            ] + extra + [
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=gid",
            "-overwrite",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return JsonResponse({
                "error": "ogr2ogr CLI failed",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "chosen_nlt":   nlt
            }, status=500)
    else:
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

    # 6) Publish to GeoServer REST
    gs    = settings.GEOSERVER_URL.rstrip('/')
    auth  = (settings.GEOSERVER_USER, settings.GEOSERVER_PASS)
    ws     = "roles_test"
    store  = "postgres" 

    # 6a) Create datastore if needed
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

    # 6b) Publish the featureType, injecting our dynamic SRS
    ft_url = f"{gs}/rest/workspaces/{ws}/datastores/{store}/featuretypes"
    
    ft_xml = f"""
    <featureType>
      <name>{layer_name}</name>
      <nativeName>{layer_name}</nativeName>
      <title>{layer_name}</title>
      <srs>{srs_code}</srs>
    </featureType>
    """
    r = requests.post(ft_url, auth=auth,
                      headers={"Content-Type": "text/xml"},
                      data=ft_xml)
    if not r.ok:
        return JsonResponse({
            "error": "GeoServer publish failed",
            "details": r.text
        }, status=500)

    # 7) Success!
    return JsonResponse({
        "success":    True,
        "layer":      layer_name,
        "srs":        srs_code,
        "chosen_nlt": nlt
    })
