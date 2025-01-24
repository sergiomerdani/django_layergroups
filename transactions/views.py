from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

class DrawFeatureAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract parameters from the request payload
        layer_name = request.data.get("layerName")
        workspace = request.data.get("workspace")
        formatted_coordinates = request.data.get("formattedCoordinates")
        layer_type = request.data.get("layerType")  # "Point", "LineString", or "Polygon"
        host = request.data.get("host", "localhost")  # Default to localhost if not provided

        if not (layer_name and workspace and formatted_coordinates and layer_type):
            return Response(
                {"error": "Missing required parameters: layerName, workspace, layerType, or formattedCoordinates"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate the WFS Transaction XML
        try:
            wfs_transaction = self.generate_wfs_transaction(
                layer_name, workspace, layer_type, formatted_coordinates, host
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send the WFS Transaction request to GeoServer
        geoserver_url = f"http://{host}:8080/geoserver/{workspace}/ows"
        headers = {"Content-Type": "text/xml"}

        try:
            response = requests.post(geoserver_url, data=wfs_transaction, headers=headers)
            if response.status_code == 200:
                return Response({"message": "Feature added successfully", "details": response.text}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "GeoServer error", "details": response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_wfs_transaction(self, layer_name, workspace, layer_type, formatted_coordinates, host):
        if layer_type == "LineString":
            return f"""
            <wfs:Transaction service="WFS" version="1.1.0"
            xmlns:wfs="http://www.opengis.net/wfs"
            xmlns:test="http://www.openplans.org/test"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-transaction.xsd http://www.openplans.org http://{host}:8080/geoserver/wfs/DescribeFeatureType?typename=test:line">
            <wfs:Insert>
              <{layer_name}>
                <{workspace}:geom>
                  <gml:MultiLineString srsName="http://www.opengis.net/gml/srs/epsg.xml#3857">
                    <gml:lineStringMember>
                      <gml:LineString>
                        <gml:coordinates decimal="." cs="," ts=" ">
                        {formatted_coordinates}
                        </gml:coordinates>
                      </gml:LineString>
                    </gml:lineStringMember>
                  </gml:MultiLineString>
                </{workspace}:geom>
                <{workspace}:TYPE>alley</{workspace}:TYPE>
              </{layer_name}>
            </wfs:Insert>
            </wfs:Transaction>
            """
        elif layer_type == "Polygon":
            return f"""
            <wfs:Transaction service="WFS" version="1.1.0"
            xmlns:wfs="http://www.opengis.net/wfs"
            xmlns:test="http://www.openplans.org/test"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-transaction.xsd http://www.openplans.org http://{host}:8080/geoserver/wfs/DescribeFeatureType?typename=test:line">
            <wfs:Insert>
              <{layer_name}>
                <{workspace}:geom>
                  <gml:MultiLineString srsName="http://www.opengis.net/gml/srs/epsg.xml#3857">
                    <gml:lineStringMember>
                      <gml:LineString>
                        <gml:coordinates decimal="." cs="," ts=" ">
                        {formatted_coordinates}
                        </gml:coordinates>
                      </gml:LineString>
                    </gml:lineStringMember>
                  </gml:MultiLineString>
                </{workspace}:geom>
                <{workspace}:TYPE>alley</{workspace}:TYPE>
              </{layer_name}>
            </wfs:Insert>
            </wfs:Transaction>
            """
        elif layer_type == "Point":
            return f"""
            <wfs:Transaction service="WFS" version="1.1.0"
            xmlns:wfs="http://www.opengis.net/wfs"
            xmlns:test="http://www.openplans.org/test"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-transaction.xsd http://www.openplans.org http://{host}:8080/geoserver/wfs/DescribeFeatureType?typename=test:points">
            <wfs:Insert>
              <{layer_name}>
                <{workspace}:geom>
                  <gml:Point srsDimension="2" srsName="urn:x-ogc:def:crs:EPSG:3857">
                  <gml:coordinates xmlns:gml="http://www.opengis.net/gml"
                  decimal="." cs="," ts=" ">{formatted_coordinates}</gml:coordinates>
                  </gml:Point>
                </{workspace}:geom>
                <{workspace}:TYPE>alley</{workspace}:TYPE>
              </{layer_name}>
            </wfs:Insert>
            </wfs:Transaction>
            """
        else:
            raise ValueError("Unsupported geometry type")
