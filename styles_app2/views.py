import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    list_styles,
    get_style,
    create_geoserver_style,
    update_style,
    delete_style
)

@api_view(["GET", "POST"])
def styles_list_create_view(request):
    """
    GET  -> List all styles
    POST -> Create a new style
    """
    if request.method == "GET":
        # List all styles
        try:
            data = list_styles()
            return Response(data)
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)

    elif request.method == "POST":
        """
        Create a new style in GeoServer.
        """
        style_data = request.data  # Expecting JSON with style details
        try:
            geoserver_response = create_geoserver_style(style_data)
            if geoserver_response['success']:
                return Response(
                    {"message": "Style created successfully in GeoServer."},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": geoserver_response['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET", "PUT", "DELETE"])
def style_detail_view(request, style_name):
    """
    GET    -> Retrieve details of a style
    PUT    -> Update style (SLD body)
    DELETE -> Delete style
    """
    
    
    if request.method == "GET":
        try:
            data = get_style(style_name)
            return Response(data)
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)

    elif request.method == "PUT":
    # Expecting JSON payload
        style_data = request.data

        try:
            # Update the style using the JSON data
            geoserver_response = update_style(style_name, style_data)
            if geoserver_response["success"]:
                return Response({"message": geoserver_response["message"]}, status=status.HTTP_200_OK)
            else:
                return Response({"error": geoserver_response["message"]}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        try:
            delete_style(style_name)
            return Response({"message": "Style deleted successfully"})
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)
