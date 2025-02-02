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
                # Get the new style parameters from the request body (JSON payload).
                new_style_data = request.data
                
                # Optionally, force the style name in the payload to match the URL parameter.
                new_style_data["name"] = style_name

                result = update_geoserver_style_from_json(style_name, new_style_data)
                status_code = 200 if result.get("success") else 400
                return Response(result, status=status_code)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)