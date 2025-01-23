# utils.py
import requests

GEOSERVER_BASE_URL = "http://localhost:8080/geoserver/rest/workspaces/finiq_ws"
AUTH = ("admin", "geoserver")  # Replace with your GeoServer credentials

def list_styles():
    """
    Retrieve a list of all styles on the GeoServer.
    """
    url = f"{GEOSERVER_BASE_URL}/styles.json"
    response = requests.get(url, auth=AUTH)
    response.raise_for_status()
    return response.json()

def get_style(style_name):
    """
    Retrieve details of a specific style by name.
    """
    url = f"{GEOSERVER_BASE_URL}/styles/{style_name}.json"
    response = requests.get(url, auth=AUTH)
    response.raise_for_status()
    return response.json()

def create_geoserver_style(style_data):
    """
    Create a style in GeoServer using REST API.
    """
    if "name" not in style_data:
        raise ValueError("The 'name' field is required.")
    if "style_type" not in style_data:
        raise ValueError("The 'style_type' field is required.")

    sld_body = generate_sld(style_data)  # Generate SLD dynamically

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
    Dynamically generate SLD XML based on style data.
    """
    style_type = style_data.get("style_type")
    name = style_data.get("name")
    fill_color = style_data.get("fill_color", "#000000")
    stroke_color = style_data.get("stroke_color", "#000000")
    stroke_width = style_data.get("stroke_width", 1)
    size = style_data.get("size", 5)
    fill_opacity = style_data.get("fill_opacity", 1)

    if style_type == "polygon":
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">
            <NamedLayer>
                <Name>{name}</Name>
                <UserStyle>
                    <FeatureTypeStyle>
                        <Rule>
                            <PolygonSymbolizer>
                                <Fill>
                                    <CssParameter name="fill">{fill_color}</CssParameter>
                                    <CssParameter name="fill-opacity">{fill_opacity}</CssParameter>
                                </Fill>
                                <Stroke>
                                    <CssParameter name="stroke">{stroke_color}</CssParameter>
                                    <CssParameter name="stroke-width">{stroke_width}</CssParameter>
                                </Stroke>
                            </PolygonSymbolizer>
                        </Rule>
                    </FeatureTypeStyle>
                </UserStyle>
            </NamedLayer>
        </StyledLayerDescriptor>
        """
    elif style_type == "line":
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">
            <NamedLayer>
                <Name>{name}</Name>
                <UserStyle>
                    <FeatureTypeStyle>
                        <Rule>
                            <LineSymbolizer>
                                <Stroke>
                                    <CssParameter name="stroke">{stroke_color}</CssParameter>
                                    <CssParameter name="stroke-width">{stroke_width}</CssParameter>
                                </Stroke>
                            </LineSymbolizer>
                        </Rule>
                    </FeatureTypeStyle>
                </UserStyle>
            </NamedLayer>
        </StyledLayerDescriptor>
        """
    elif style_type == "point":
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">
            <NamedLayer>
                <Name>{name}</Name>
                <UserStyle>
                    <FeatureTypeStyle>
                        <Rule>
                            <PointSymbolizer>
                                <Graphic>
                                    <Mark>
                                        <WellKnownName>circle</WellKnownName>
                                        <Fill>
                                            <CssParameter name="fill">{fill_color}</CssParameter>
                                        </Fill>
                                        <Stroke>
                                            <CssParameter name="stroke">{stroke_color}</CssParameter>
                                            <CssParameter name="stroke-width">{stroke_width}</CssParameter>
                                        </Stroke>
                                    </Mark>
                                    <Size>{size}</Size>
                                </Graphic>
                            </PointSymbolizer>
                        </Rule>
                    </FeatureTypeStyle>
                </UserStyle>
            </NamedLayer>
        </StyledLayerDescriptor>
        """
    else:
        raise ValueError("Invalid style type. Must be 'point', 'line', or 'polygon'.")

def update_style(style_name, style_data):
    """
    Update (replace) the style content of an existing style using JSON data.
    """
    # Convert JSON payload to SLD
    sld_body = generate_sld(style_data)  # Dynamically generate the SLD based on the JSON input

    # Prepare GeoServer REST API URL
    url = f"{GEOSERVER_BASE_URL}/styles/{style_name}"
    headers = {"Content-Type": "application/vnd.ogc.sld+xml"}

    # Send the updated SLD to GeoServer
    response = requests.put(url, auth=AUTH, headers=headers, data=sld_body)
    
    # Handle response
    if response.status_code in [200, 201]:
        return {"success": True, "message": "Style updated successfully"}
    else:
        return {"success": False, "message": response.text}

def delete_style(style_name):
    """
    Delete a style by name.
    """
    url = f"{GEOSERVER_BASE_URL}/styles/{style_name}"
    response = requests.delete(url, auth=AUTH)
    response.raise_for_status()
    return True
