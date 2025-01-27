import requests

GEOSERVER_BASE_URL = "http://localhost:8080/geoserver/rest/workspaces/finiq_ws"
AUTH = ("admin", "geoserver")  # Replace with your GeoServer credentials

def create_geoserver_style(style_data):
    """
    Create a style in GeoServer using REST API with advanced styling options.
    """
    if "name" not in style_data:
        raise ValueError("The 'name' field is required.")
    if "style_type" not in style_data:
        raise ValueError("The 'style_type' field is required.")

    sld_body = generate_advanced_sld(style_data)

    headers = {'Content-Type': 'application/vnd.ogc.sld+xml'}
    response = requests.post(
        f"{GEOSERVER_BASE_URL}/styles",
        auth=AUTH,
        params={'name': style_data['name']},
        data=sld_body,
        headers=headers
    )

    if response.status_code in [200, 201]:
        return {'success': True}
    else:
        return {'success': False, 'message': response.text}


def generate_advanced_sld(style_data):
    """
    Generate SLD XML (1.0.0) with proper colors and labels for polygon, line, and point types.
    """
    style_name = style_data.get("name", "default_style")
    layer_name = style_data.get("layer_name", "default_layer")
    style_type = style_data.get("style_type", "polygon")  # Default to polygon

    # Shared parameters
    stroke_color = style_data.get("stroke_color", "#000000")  # Default to black
    stroke_width = style_data.get("stroke_width", 1)
    stroke_opacity = style_data.get("stroke_opacity", 1)  # Used for line and point types
    label_field = style_data.get("label_field")
    font_family = style_data.get("font_family", "Serif")
    font_size = style_data.get("font_size", 10)
    font_color = style_data.get("font_color", "#000000")

    # Polygon-specific parameters
    fill_color = style_data.get("fill_color", "#FFFFFF")  # Default to white
    fill_opacity = style_data.get("fill_opacity", 1)

    # Point-specific parameters
    point_size = style_data.get("point_size", 10)  # Default size for point symbols
    point_shape = style_data.get("point_shape", "circle")  # Default shape is a circle

    # Base SLD structure
    sld_header = f"""
    <sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld"
                               xmlns:gml="http://www.opengis.net/gml"
                               xmlns:ogc="http://www.opengis.net/ogc"
                               version="1.0.0">
        <sld:NamedLayer>
            <sld:Name>{layer_name}</sld:Name>
            <sld:UserStyle>
                <sld:Name>{style_name}</sld:Name>
                <sld:FeatureTypeStyle>
                    <sld:Rule>
                        <sld:Name>Single symbol</sld:Name>
    """

    # Style-specific symbolizer
    if style_type == "polygon":
        sld_header += f"""
                        <sld:PolygonSymbolizer>
                            <sld:Fill>
                                <sld:CssParameter name="fill">{fill_color}</sld:CssParameter>
                                <sld:CssParameter name="fill-opacity">{fill_opacity}</sld:CssParameter>
                            </sld:Fill>
                            <sld:Stroke>
                                <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
                                <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
                            </sld:Stroke>
                        </sld:PolygonSymbolizer>
        """
    elif style_type == "line":
        sld_header += f"""
                        <sld:LineSymbolizer>
                            <sld:Stroke>
                                <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
                                <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
                                <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
                            </sld:Stroke>
                        </sld:LineSymbolizer>
        """
    elif style_type == "point":
        sld_header += f"""
                        <sld:PointSymbolizer>
                            <sld:Graphic>
                                <sld:Mark>
                                    <sld:WellKnownName>{point_shape}</sld:WellKnownName>
                                    <sld:Fill>
                                        <sld:CssParameter name="fill">{fill_color}</sld:CssParameter>
                                        <sld:CssParameter name="fill-opacity">{fill_opacity}</sld:CssParameter>
                                    </sld:Fill>
                                    <sld:Stroke>
                                        <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
                                        <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
                                    </sld:Stroke>
                                </sld:Mark>
                                <sld:Size>{point_size}</sld:Size>
                            </sld:Graphic>
                        </sld:PointSymbolizer>
        """

    # Add label configuration if a label field is provided
    if label_field:
        sld_header += f"""
                    </sld:Rule>
                    <sld:Rule>
                        <sld:TextSymbolizer>
                            <sld:Label>
                                <ogc:PropertyName>{label_field}</ogc:PropertyName>
                            </sld:Label>
                            <sld:Font>
                                <sld:CssParameter name="font-family">{font_family}</sld:CssParameter>
                                <sld:CssParameter name="font-size">{font_size}</sld:CssParameter>
                                <sld:CssParameter name="font-style">normal</sld:CssParameter>
                                <sld:CssParameter name="font-weight">normal</sld:CssParameter>
                            </sld:Font>
                            <sld:LabelPlacement>
                                <sld:PointPlacement>
                                    <sld:AnchorPoint>
                                        <sld:AnchorPointX>0.5</sld:AnchorPointX>
                                        <sld:AnchorPointY>0.5</sld:AnchorPointY>
                                    </sld:AnchorPoint>
                                </sld:PointPlacement>
                            </sld:LabelPlacement>
                            <sld:Fill>
                                <sld:CssParameter name="fill">{font_color}</sld:CssParameter>
                            </sld:Fill>
                        </sld:TextSymbolizer>
        """

    # Close the SLD structure
    sld_footer = """
                    </sld:Rule>
                </sld:FeatureTypeStyle>
            </sld:UserStyle>
        </sld:NamedLayer>
    </sld:StyledLayerDescriptor>
    """

    return sld_header + sld_footer
