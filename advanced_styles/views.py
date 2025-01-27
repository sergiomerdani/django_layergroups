from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import create_geoserver_style

@api_view(['POST'])
def create_style(request):
    """
    API to create a new style in GeoServer.
    """
    try:
        style_data = request.data
        result = create_geoserver_style(style_data)
        return Response(result, status=200 if result['success'] else 400)
    except Exception as e:
        return Response({'success': False, 'message': str(e)}, status=400)
