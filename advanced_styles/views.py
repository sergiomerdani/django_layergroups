from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import create_geoserver_style,get_geoserver_styles,get_geoserver_style,delete_geoserver_style,update_geoserver_style_from_json

@api_view(['GET','POST'])
def fetch_create_style(request):
    """
    API to create a new style in GeoServer (POST) or fetch all styles in a workspace (GET).
    """
    if request.method == 'POST':
        try:
            style_data = request.data
            result = create_geoserver_style(style_data)
            return Response(result, status=200 if result['success'] else 400)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)
    elif request.method == 'GET':
        result = get_geoserver_styles()
        return Response(result, status=200 if result['success'] else 400)

@api_view(['GET','PUT','DELETE'])
def style_detail(request, style_name):
    """
    API to get details of a specific style (GET) or delete a style (DELETE).
    """
    if request.method == 'GET':
        result = get_geoserver_style(style_name)
        return Response(result, status=200 if result['success'] else 400)

    elif request.method == 'DELETE':
        result = delete_geoserver_style(style_name)
        return Response(result, status=200 if result['success'] else 400)
    
    elif request.method == 'PUT':
        try:
            new_style_data = request.data  # Expecting JSON payload
            if "name" not in new_style_data:
                return Response({'success': False, 'message': 'Style name is required'}, status=400)

            result = update_geoserver_style_from_json(style_name, new_style_data)
            return Response(result, status=200 if result['success'] else 400)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)