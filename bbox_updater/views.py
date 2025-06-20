import psycopg2
import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET","PUT"])
def update_bbox(request, layer_name):
    db_config = {
        "dbname": "postgis_sample",
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": 5432
    }

    workspace = "roles_test"
    datastore = "postgres"
    geoserver_url = "http://localhost:8080"
    geoserver_user = "admin"
    geoserver_pass = "geoserver"

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT 
              ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext),
              ST_XMin(ext_4326), ST_YMin(ext_4326), ST_XMax(ext_4326), ST_YMax(ext_4326)
            FROM (
              SELECT 
                ST_Extent(geom) AS ext,
                ST_Extent(ST_Transform(geom, 4326)) AS ext_4326
              FROM {layer_name}
            ) AS sub;
        """)
        row = cur.fetchone()
        print(f"Fetched row: {row}")
        cur.close()
        conn.close()

        if not row or None in row:
            return Response({"error": f"No bounding box found for {layer_name}"}, status=400)

        minx, miny, maxx, maxy, lon_min, lat_min, lon_max, lat_max = row

        payload = {
            "featureType": {
                "nativeBoundingBox": {
                    "minx": minx, "miny": miny,
                    "maxx": maxx, "maxy": maxy,
                    "crs": "EPSG:3857"
                },
                "latLonBoundingBox": {
                    "minx": lon_min, "miny": lat_min,
                    "maxx": lon_max, "maxy": lat_max,
                    "crs": "EPSG:4326"
                }
            }
        }

        url = f"{geoserver_url}/geoserver/rest/workspaces/{workspace}/datastores/{datastore}/featuretypes/{layer_name}"
        response = requests.put(
            url,
            auth=(geoserver_user, geoserver_pass),
            headers={"Content-Type": "application/json"},
            json=payload
        )

        if response.status_code in (200, 201):
            return Response({"message": f"Bounding box updated for {layer_name}"})
        return Response({"error": response.text}, status=response.status_code)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
