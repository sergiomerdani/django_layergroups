from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import create_geoserver_style

class GeoStyleView(APIView):
    def post(self, request):
        style_data = request.data  # Expecting JSON with style details
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
