from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import psycopg2
from psycopg2 import sql
import requests

GEOSERVER_SETTINGS = {
    "url": "http://localhost:8080/geoserver",
    "workspace": "finiq_ws",
    "datastore": "finiqi_data",
    "auth": ("admin", "geoserver"),  # Replace with your credentials
}

# Database connection settings
DB_SETTINGS = {
    "dbname": "bashkia_finiq",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

@api_view(["POST"])
def manage_columns(request):
    """
    API to add or delete columns in a PostgreSQL table.
    """
    action = request.data.get("action")  # "add" or "delete"
    table_name = request.data.get("table_name")
    column_name = request.data.get("column_name")
    column_type = request.data.get("column_type", None)  # Required for adding columns

    if not table_name or not column_name:
        return Response(
            {"error": "Both 'table_name' and 'column_name' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**DB_SETTINGS)
        cursor = conn.cursor()

        if action == "add":
            if not column_type:
                return Response(
                    {"error": "'column_type' is required to add a column."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add column SQL
            query = sql.SQL(
                "ALTER TABLE {table} ADD COLUMN {column} {ctype}"
            ).format(
                table=sql.Identifier(table_name),
                column=sql.Identifier(column_name),
                ctype=sql.SQL(column_type),
            )
            cursor.execute(query)
            conn.commit()
            message = f"Column '{column_name}' of type '{column_type}' added to table '{table_name}'."

        elif action == "delete":
            # Delete column SQL
            query = sql.SQL(
                "ALTER TABLE {table} DROP COLUMN {column}"
            ).format(
                table=sql.Identifier(table_name),
                column=sql.Identifier(column_name),
            )
            cursor.execute(query)
            conn.commit()
            message = f"Column '{column_name}' deleted from table '{table_name}'."

        else:
            return Response(
                {"error": "'action' must be either 'add' or 'delete'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reload the datastore in GeoServer
        reload_url = f"{GEOSERVER_SETTINGS['url']}/rest/reload"
        reload_response = requests.post(reload_url, auth=GEOSERVER_SETTINGS["auth"])


        if reload_response.status_code in (200, 204):
            message += " Datastore reloaded successfully."
        else:
            message += " Datastore reload failed."
            print("Datastore Reload Error:", reload_response.text)

        return Response({"message": message}, status=status.HTTP_200_OK)

    except psycopg2.Error as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        if conn:
            cursor.close()
            conn.close()
