import requests
from requests.auth import HTTPBasicAuth

GEOSERVER_BASE_URL = "http://localhost:8080/geoserver/rest/workspaces/finiq_ws"
AUTH = ("admin", "geoserver")  # Replace with your GeoServer credentials

def get_geoserver_styles():
    """
    Fetch all styles in the specified GeoServer workspace.
    """
    try:
        styles_url = f"{GEOSERVER_BASE_URL}/styles.json"
        response = requests.get(styles_url, auth=HTTPBasicAuth(*AUTH))

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}

def create_geoserver_style(style_data):
    """
    Create a style in GeoServer using REST API with advanced styling options.
    """
    if "name" not in style_data:
        raise ValueError("The 'name' field is required.")
    if "style_type" not in style_data:
        raise ValueError("The 'style_type' field is required.")

    sld_body = generate_sld(style_data)

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

def generate_sld(style_data):
    """
    Generate SLD XML (1.0.0) for single or rule-based styling for polygon, line, and point types,
    including dynamic labeling support.
    """
    style_name = style_data.get("name", "default_style")
    layer_name = style_data.get("layer_name", "default_layer")
    style_type = style_data.get("style_type", "single")  # Default to single style

    # Shared parameters
    field_name = style_data.get("field_name")  # Field for rule-based styling
    rules = style_data.get("rules", [])  # List of rules for rule-based styling
    stroke_color = style_data.get("stroke_color", "#000000")
    stroke_width = style_data.get("stroke_width", 1)
    stroke_opacity = style_data.get("stroke_opacity", 1)

    # Polygon-specific parameters
    fill_color = style_data.get("fill_color", "#FFFFFF")
    fill_opacity = style_data.get("fill_opacity", 1)

    # Point-specific parameters
    point_size = style_data.get("point_size", 10)
    point_shape = style_data.get("point_shape", "circle")

    # Labeling parameters
    label_enabled = style_data.get("label_enabled", False)  # Whether labeling is enabled
    label_field = style_data.get("label_field", None)  # Field for labeling
    font_family = style_data.get("font_family", "Arial")
    font_size = style_data.get("font_size", 10)
    font_color = style_data.get("font_color", "#000000")
    font_style = style_data.get("font_style", "normal")
    font_weight = style_data.get("font_weight", "normal")

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
    """
        # Rule-based symbology
    if style_type == "rule":
        if not field_name:
            raise ValueError("Field name is required for rule-based symbology.")
        for rule in rules:
            rule_name = rule.get("name", "Unnamed Rule")
            rule_value = rule.get("value")  # The unique value for the field
            rule_fill_color = rule.get("fill_color", fill_color)
            rule_fill_opacity = rule.get("fill_opacity", fill_opacity)
            rule_stroke_color = rule.get("stroke_color", stroke_color)
            rule_stroke_width = rule.get("stroke_width", stroke_width)
            rule_point_size = rule.get("point_size", point_size)
            rule_point_shape = rule.get("point_shape", point_shape)

            sld_header += f"""
                    <sld:Rule>
                        <sld:Name>{rule_name}</sld:Name>
                        <sld:Filter>
                            <ogc:PropertyIsEqualTo>
                                <ogc:PropertyName>{field_name}</ogc:PropertyName>
                                <ogc:Literal>{rule_value}</ogc:Literal>
                            </ogc:PropertyIsEqualTo>
                        </sld:Filter>
            """
            if rule.get("geometry_type") == "polygon":
                sld_header += f"""
                        <sld:PolygonSymbolizer>
                            <sld:Fill>
                                <sld:CssParameter name="fill">{rule_fill_color}</sld:CssParameter>
                                <sld:CssParameter name="fill-opacity">{rule_fill_opacity}</sld:CssParameter>
                            </sld:Fill>
                            <sld:Stroke>
                                <sld:CssParameter name="stroke">{rule_stroke_color}</sld:CssParameter>
                                <sld:CssParameter name="stroke-width">{rule_stroke_width}</sld:CssParameter>
                            </sld:Stroke>
                        </sld:PolygonSymbolizer>
                """
            elif rule.get("geometry_type") == "line":
                sld_header += f"""
                        <sld:LineSymbolizer>
                            <sld:Stroke>
                                <sld:CssParameter name="stroke">{rule_stroke_color}</sld:CssParameter>
                                <sld:CssParameter name="stroke-width">{rule_stroke_width}</sld:CssParameter>
                                <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
                            </sld:Stroke>
                        </sld:LineSymbolizer>
                """
            elif rule.get("geometry_type") == "point":
                sld_header += f"""
                    <sld:PointSymbolizer>
                        <sld:Graphic>
                            <sld:Mark>
                                <sld:WellKnownName>{rule_point_shape}</sld:WellKnownName>
                                <sld:Fill>
                                    <sld:CssParameter name="fill">{rule_fill_color}</sld:CssParameter>
                                    <sld:CssParameter name="fill-opacity">{rule_fill_opacity}</sld:CssParameter>
                                </sld:Fill>
                                <sld:Stroke>
                                    <sld:CssParameter name="stroke">{rule_stroke_color}</sld:CssParameter>
                                    <sld:CssParameter name="stroke-width">{rule_stroke_width}</sld:CssParameter>
                                </sld:Stroke>
                            </sld:Mark>
                            <sld:Size>{rule_point_size}</sld:Size>
                        </sld:Graphic>
                    </sld:PointSymbolizer>
                """
            sld_header += "</sld:Rule>"

    else:
        # Single symbol logic
        if style_data.get("geometry_type") == "point":
            sld_header += f"""
                        <sld:Rule>
                            <sld:Name>Single symbol</sld:Name>
                            <sld:PointSymbolizer>
                                <sld:Graphic>
                                    <sld:Mark>
                                        <sld:WellKnownName>{style_data.get("point_shape", "circle")}</sld:WellKnownName>
                                        <sld:Fill>
                                            <sld:CssParameter name="fill">{style_data.get("fill_color", "#FF0000")}</sld:CssParameter>
                                            <sld:CssParameter name="fill-opacity">{style_data.get("fill_opacity", 1)}</sld:CssParameter>
                                        </sld:Fill>
                                        <sld:Stroke>
                                            <sld:CssParameter name="stroke">{style_data.get("stroke_color", "#000000")}</sld:CssParameter>
                                            <sld:CssParameter name="stroke-width">{style_data.get("stroke_width", 1)}</sld:CssParameter>
                                        </sld:Stroke>
                                    </sld:Mark>
                                    <sld:Size>{style_data.get("point_size", 10)}</sld:Size>
                                </sld:Graphic>
                            </sld:PointSymbolizer>
                        </sld:Rule>
            """
        elif style_data.get("geometry_type") == "line":
            sld_header += f"""
                        <sld:Rule>
                            <sld:Name>Single symbol</sld:Name>
                            <sld:LineSymbolizer>
                                <sld:Stroke>
                                    <sld:CssParameter name="stroke">{style_data.get("stroke_color", "#000000")}</sld:CssParameter>
                                    <sld:CssParameter name="stroke-width">{style_data.get("stroke_width", 1)}</sld:CssParameter>
                                    <sld:CssParameter name="stroke-opacity">{style_data.get("stroke_opacity", 1)}</sld:CssParameter>
                                </sld:Stroke>
                            </sld:LineSymbolizer>
                        </sld:Rule>
            """
        elif style_data.get("geometry_type") == "polygon":
            sld_header += f"""
                        <sld:Rule>
                            <sld:Name>Single symbol</sld:Name>
                            <sld:PolygonSymbolizer>
                                <sld:Fill>
                                    <sld:CssParameter name="fill">{style_data.get("fill_color", "#FFFFFF")}</sld:CssParameter>
                                    <sld:CssParameter name="fill-opacity">{style_data.get("fill_opacity", 1)}</sld:CssParameter>
                                </sld:Fill>
                                <sld:Stroke>
                                    <sld:CssParameter name="stroke">{style_data.get("stroke_color", "#000000")}</sld:CssParameter>
                                    <sld:CssParameter name="stroke-width">{style_data.get("stroke_width", 1)}</sld:CssParameter>
                                </sld:Stroke>
                            </sld:PolygonSymbolizer>
                        </sld:Rule>
            """


    # Add labeling if enabled
    if label_enabled and label_field:
        sld_header += f"""
                    <sld:Rule>
                        <sld:TextSymbolizer>
                            <sld:Label>
                                <ogc:PropertyName>{label_field}</ogc:PropertyName>
                            </sld:Label>
                            <sld:Font>
                                <sld:CssParameter name="font-family">{font_family}</sld:CssParameter>
                                <sld:CssParameter name="font-size">{font_size}</sld:CssParameter>
                                <sld:CssParameter name="font-style">{font_style}</sld:CssParameter>
                                <sld:CssParameter name="font-weight">{font_weight}</sld:CssParameter>
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
                    </sld:Rule>
        """

    # Close the SLD structure
    sld_footer = """
                </sld:FeatureTypeStyle>
            </sld:UserStyle>
        </sld:NamedLayer>
    </sld:StyledLayerDescriptor>
    """

    return sld_header + sld_footer

def get_geoserver_style(style_name):
    """
    Fetch details of a specific style in the GeoServer workspace.
    """
    try:
        style_url = f"{GEOSERVER_BASE_URL}/styles/{style_name}.json"
        response = requests.get(style_url, auth=HTTPBasicAuth(*AUTH))

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}

def delete_geoserver_style(style_name):
    """
    Delete a specific style from the GeoServer workspace.
    """
    try:
        style_url = f"{GEOSERVER_BASE_URL}/styles/{style_name}"
        response = requests.delete(style_url, auth=HTTPBasicAuth(*AUTH))

        if response.status_code in [200, 204]:
            return {"success": True, "message": f"Style '{style_name}' deleted successfully"}
        else:
            return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
def update_geoserver_style_from_json(style_name, new_style_data):
    """
    Update an existing style in GeoServer by completely recreating its SLD
    from the provided JSON payload. This function generates a new SLD (using
    generate_sld()) and sends it via a PUT request, effectively replacing the old style.
    """
    try:
        # (Optional) If you want to preserve the existing geometry type,
        # you can fetch the current metadata and then update new_style_data accordingly.
        metadata_url = f"{GEOSERVER_BASE_URL}/styles/{style_name}.json"
        response = requests.get(metadata_url, auth=HTTPBasicAuth(*AUTH))
        if response.status_code == 200:
            existing_style = response.json().get("style", {})
            # If the new payload does not include a geometry type, preserve the existing one.
            if "geometry_type" not in new_style_data or not new_style_data["geometry_type"]:
                new_style_data["geometry_type"] = existing_style.get("geometry_type", "point")
        else:
            print("Warning: Could not fetch existing metadata; proceeding with provided data.")

        # Generate a brand-new SLD from the update payload.
        sld_body = generate_sld(new_style_data)
        if not sld_body:
            return {"success": False, "message": "Generated SLD is empty."}


        # Upload the new SLD to GeoServer (this will completely replace the existing style).
        update_url = f"{GEOSERVER_BASE_URL}/styles/{style_name}"
        headers = {"Content-Type": "application/vnd.ogc.sld+xml"}
        response = requests.put(update_url, auth=HTTPBasicAuth(*AUTH), data=sld_body, headers=headers)

        if response.status_code in [200, 201]:
            return {"success": True, "message": f"Style '{style_name}' updated successfully."}
        else:
            return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}