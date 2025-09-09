from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
import json
import re
import requests

AUTH = ("admin", "geoserver")  # 🔑 adjust credentials
GEOSERVER_URL = "http://localhost:8080/geoserver"
WORKSPACE = "test"
DATASTORE = "postgres"


@csrf_exempt
def site_selection(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)
    candidate_layer_name = re.sub(r"[^a-zA-Z0-9_]", "", data.get("candidateLayerName", ""))
    demand_layer = data.get("demandLayer")
    facilities_layer = data.get("facilitiesLayer")
    D = data.get("D")
    minLib = data.get("minLib")
    grid = data.get("grid")
    K = data.get("K")

    try:
        # ✅ Step 1: Check if layer already exists
        featuretype_url = (
            f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes/{candidate_layer_name}.json"
        )
        r = requests.get(featuretype_url, auth=AUTH)

        if r.status_code == 404:
            # ❌ Not found → create new featuretype
            create_url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes"
            payload = {
                "featureType": {
                    "name": candidate_layer_name,
                    "nativeCRS": "EPSG:3857",
                    "srs": "EPSG:3857",
                    "attributes": {
                        "attribute": [
                            {"name": "fid", "binding": "java.lang.Long"},
                            {"name": "geom", "binding": "org.locationtech.jts.geom.Point"},
                            {"name": "demand_covered", "binding": "java.lang.Integer"},
                            {"name": "avg_dist", "binding": "java.lang.Double"},
                            {"name": "radius_m", "binding": "java.lang.Double"},
                            {"name": "grid_m", "binding": "java.lang.Double"},
                            {"name": "min_from_lib_m", "binding": "java.lang.Double"},
                        ]
                    },
                }
            }
            cr = requests.post(
                create_url,
                json=payload,
                auth=AUTH,
                headers={"Content-Type": "application/json"},
            )
            if cr.status_code not in (200, 201):
                return JsonResponse({"error": f"GeoServer create failed: {cr.text}"}, status=500)

        elif r.status_code not in (200, 201):
            return JsonResponse({"error": f"GeoServer check failed: {r.text}"}, status=500)
        else:
            print(f"✅ Layer {candidate_layer_name} already exists, skipping creation")

        # ✅ Step 2: Insert computed candidates into Postgres table
        with connection.cursor() as cursor:
    # ✅ Step 2: Insert computed candidates
            libs_cte = (
                f"""
                libs AS (
                SELECT ST_Transform(geom, 4326)::geography AS g
                FROM public."{facilities_layer}"
                WHERE geom IS NOT NULL
                ),
                """
                if facilities_layer
                else """
                libs AS (
                SELECT NULL::geography AS g
                WHERE FALSE
                ),
                """
            )

            insert_sql = f"""
            INSERT INTO public."{candidate_layer_name}"
            (geom, demand_covered, avg_dist, radius_m, grid_m, min_from_lib_m)
            WITH RECURSIVE
            params AS (
            SELECT
                %s::float8 AS D,
                %s::float8 AS grid_m,
                %s::float8 AS min_from_lib_m,
                %s::int    AS K
            ),
            {libs_cte}
            schools AS (
            SELECT fid, ST_Transform(geom, 4326)::geography AS g
            FROM public."{demand_layer}" s
            WHERE geom IS NOT NULL
                AND NOT EXISTS (
                SELECT 1
                FROM libs l
                WHERE ST_DWithin(
                    ST_Transform(s.geom, 4326)::geography,
                    l.g,
                    (SELECT D FROM params)
                )
                )
            ),
            grid_area AS (
            SELECT ST_Transform(
                    ST_Buffer(
                        ST_Union(ST_Transform(geom, 4326))::geography,
                        (SELECT D FROM params) * 2
                    )::geometry,
                    4326
                    ) AS g
            FROM public."{demand_layer}" s
            WHERE geom IS NOT NULL
                AND NOT EXISTS (
                SELECT 1
                FROM libs l
                WHERE ST_DWithin(
                    ST_Transform(s.geom, 4326)::geography,
                    l.g,
                    (SELECT D FROM params)
                )
                )
            ),
            grid_cells AS (
            SELECT ST_Transform(geom, 4326) AS cell
            FROM ST_HexagonGrid(
                    (SELECT grid_m FROM params),
                    (SELECT ST_Transform(g, 3857) FROM grid_area)
                ) AS h(geom)
            ),
            candidates_ok AS (
            SELECT row_number() OVER () AS cand_id,
                    ST_PointOnSurface(cell)::geometry(Point,4326) AS geom
            FROM grid_cells
            WHERE NOT EXISTS (
                SELECT 1
                FROM libs l
                WHERE ST_DWithin(ST_PointOnSurface(cell)::geography, l.g, (SELECT min_from_lib_m FROM params))
            )
            ),
            cand_cov AS (
            SELECT c.cand_id, c.geom, s.fid AS school_id,
                    ST_Distance(c.geom::geography, s.g) AS dist
            FROM candidates_ok c
            JOIN schools s
                ON ST_DWithin(c.geom::geography, s.g, (SELECT D FROM params))
            ),
            recursion AS (
            SELECT chosen_ids, covered_schools, step
            FROM (
                SELECT 
                ARRAY[cand_id]::int[] AS chosen_ids,
                ARRAY_AGG(DISTINCT school_id)::int[] AS covered_schools,
                1::int AS step
                FROM cand_cov
                GROUP BY cand_id
                ORDER BY COUNT(DISTINCT school_id) DESC, AVG(dist) ASC
                LIMIT 1
            ) start

            UNION ALL

            SELECT
                (r.chosen_ids || nb.cand_id)::int[],
                (r.covered_schools || nb.new_cover)::int[],
                (r.step + 1)::int
            FROM recursion r
            JOIN LATERAL (
                SELECT cand_id,
                    ARRAY_AGG(DISTINCT school_id)::int[] AS new_cover
                FROM cand_cov
                WHERE cand_id <> ALL(r.chosen_ids)
                AND school_id <> ALL(r.covered_schools)
                GROUP BY cand_id
                ORDER BY COUNT(DISTINCT school_id) DESC, AVG(dist) ASC
                LIMIT 1
            ) nb ON TRUE
            WHERE r.step < (SELECT K FROM params)
                AND CARDINALITY(r.covered_schools) < (SELECT COUNT(*) FROM schools)
            ),
            final_candidates AS (
            SELECT DISTINCT unnest(chosen_ids) AS cand_id
            FROM recursion
            ),
            final_with_stats AS (
            SELECT c.geom,
                    COUNT(cov.school_id) AS demand_covered,
                    AVG(cov.dist) AS avg_dist
            FROM final_candidates fc
            JOIN candidates_ok c ON c.cand_id = fc.cand_id
            LEFT JOIN cand_cov cov ON cov.cand_id = c.cand_id
            GROUP BY c.geom
            )
            SELECT 
            ST_Transform(geom, 3857) AS geom,
            demand_covered,
            avg_dist,
            p.D AS radius_m,
            p.grid_m,
            p.min_from_lib_m
            FROM final_with_stats, params p;
            """

            cursor.execute(insert_sql, [D, grid, minLib, K])


        return JsonResponse({"status": "success", "layer": candidate_layer_name})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
