from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import create_geoserver_style, list_geoserver_styles

class GeoStyleView(APIView):
    def get(self, request):
        """
        List all styles available in GeoServer.
        """
        styles = list_geoserver_styles()
        if styles.get('success'):
            return Response(styles['data'], status=status.HTTP_200_OK)
        return Response(
            {"error": styles['message']},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def post(self, request):
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
