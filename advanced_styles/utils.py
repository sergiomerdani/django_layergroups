import requests
from requests.auth import HTTPBasicAuth

GEOSERVER_BASE_URL = "http://localhost:8080/geoserver/rest/workspaces/roles_test"
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
    including optional dynamic labeling and optional scale-denominator visibility,
    toggled the same way as labeling (on/off per layer or per rule).
    """
    # Basic style/layer identifiers
    style_name     = style_data.get("name", "default_style")
    layer_name     = style_data.get("layer_name", "default_layer")
    style_type     = style_data.get("style_type", "single")  # "single" or "rule"

    # Shared symbol parameters
    field_name     = style_data.get("field_name")             # for rule-based
    rules          = style_data.get("rules", [])
    stroke_color   = style_data.get("stroke_color", "#000000")
    stroke_width   = style_data.get("stroke_width", 1)
    stroke_opacity = style_data.get("stroke_opacity", 1)

    # Polygon fill
    fill_color     = style_data.get("fill_color", "#FFFFFF")
    fill_opacity   = style_data.get("fill_opacity", 1)

    # Point marker
    point_size     = style_data.get("point_size", 10)
    point_shape    = style_data.get("point_shape", "circle")

    # Labeling
    label_enabled  = style_data.get("label_enabled", False)
    label_field    = style_data.get("label_field")
    font_family    = style_data.get("font_family", "Arial")
    font_size      = style_data.get("font_size", 10)
    font_color     = style_data.get("font_color", "#000000")
    font_style     = style_data.get("font_style", "normal")
    font_weight    = style_data.get("font_weight", "normal")

    # Scale-visibility toggle and values
    scale_enabled  = style_data.get("scale_enabled", False)
    min_scale      = style_data.get("min_scale_denominator")
    max_scale      = style_data.get("max_scale_denominator")

    # Helper to open a Rule, injecting scale denominators only if enabled
    def open_rule(rule_name, enable_scale=False, rule_min=None, rule_max=None):
        lines = [
            "<sld:Rule>",
            f"    <sld:Name>{rule_name}</sld:Name>"
        ]
        if enable_scale:
            if rule_min is not None:
                lines.append(f"    <sld:MinScaleDenominator>{rule_min}</sld:MinScaleDenominator>")
            if rule_max is not None:
                lines.append(f"    <sld:MaxScaleDenominator>{rule_max}</sld:MaxScaleDenominator>")
        return "\n".join(lines) + "\n"

    # SLD header
    sld = f"""<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld"
                           xmlns:gml="http://www.opengis.net/gml"
                           xmlns:ogc="http://www.opengis.net/ogc"
                           version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>{layer_name}</sld:Name>
    <sld:UserStyle>
      <sld:Name>{style_name}</sld:Name>
      <sld:FeatureTypeStyle>
"""

    # Rule-based styling
    if style_type == "rule":
        if not field_name:
            raise ValueError("Field name is required for rule-based symbology.")

        for rule in rules:
            rule_name     = rule.get("name", "Unnamed Rule")
            rule_value    = rule.get("value")
            geom          = rule.get("geometry_type", style_data.get("geometry_type"))
            rule_scale_on = rule.get("scale_enabled", scale_enabled)
            rule_min      = rule.get("min_scale_denominator", min_scale)
            rule_max      = rule.get("max_scale_denominator", max_scale)
            so            = rule.get("stroke_opacity", stroke_opacity)
            # 1) open Rule with optional scales
            sld += open_rule(rule_name, rule_scale_on, rule_min, rule_max)

            # 2) Filter clause
            sld += f"""\
    <sld:Filter>
      <ogc:PropertyIsEqualTo>
        <ogc:PropertyName>{field_name}</ogc:PropertyName>
        <ogc:Literal>{rule_value}</ogc:Literal>
      </ogc:PropertyIsEqualTo>
    </sld:Filter>
"""

            # 3) Symbolizer
            if geom == "polygon":
                fc = rule.get("fill_color", fill_color)
                fo = rule.get("fill_opacity", fill_opacity)
                sc = rule.get("stroke_color", stroke_color)
                sw = rule.get("stroke_width", stroke_width)
                sld += f"""\
    <sld:PolygonSymbolizer>
      <sld:Fill>
        <sld:CssParameter name="fill">{fc}</sld:CssParameter>
        <sld:CssParameter name="fill-opacity">{fo}</sld:CssParameter>
      </sld:Fill>
      <sld:Stroke>
        <sld:CssParameter name="stroke">{sc}</sld:CssParameter>
        <sld:CssParameter name="stroke-width">{sw}</sld:CssParameter>
        <sld:CssParameter name="stroke-opacity">{so}</sld:CssParameter>
      </sld:Stroke>
    </sld:PolygonSymbolizer>
"""
            elif geom == "line":
                sc = rule.get("stroke_color", stroke_color)
                sw = rule.get("stroke_width", stroke_width)
                sld += f"""\
    <sld:LineSymbolizer>
      <sld:Stroke>
        <sld:CssParameter name="stroke">{sc}</sld:CssParameter>
        <sld:CssParameter name="stroke-width">{sw}</sld:CssParameter>
        <sld:CssParameter name="stroke-opacity">{so}</sld:CssParameter>
      </sld:Stroke>
    </sld:LineSymbolizer>
"""
            elif geom == "point":
                fc    = rule.get("fill_color", fill_color)
                fo    = rule.get("fill_opacity", fill_opacity)
                sc    = rule.get("stroke_color", stroke_color)
                sw    = rule.get("stroke_width", stroke_width)
                ps    = rule.get("point_size", point_size)
                shape = rule.get("point_shape", point_shape)
                sld += f"""\
    <sld:PointSymbolizer>
      <sld:Graphic>
        <sld:Mark>
          <sld:WellKnownName>{shape}</sld:WellKnownName>
          <sld:Fill>
            <sld:CssParameter name="fill">{fc}</sld:CssParameter>
            <sld:CssParameter name="fill-opacity">{fo}</sld:CssParameter>
          </sld:Fill>
          <sld:Stroke>
            <sld:CssParameter name="stroke">{sc}</sld:CssParameter>
            <sld:CssParameter name="stroke-width">{sw}</sld:CssParameter>
            <sld:CssParameter name="stroke-opacity">{so}</sld:CssParameter>
          </sld:Stroke>
        </sld:Mark>
        <sld:Size>{ps}</sld:Size>
      </sld:Graphic>
    </sld:PointSymbolizer>
"""

            # 4) Label inside the same rule
            if label_enabled and label_field:
                sld += f"""\
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
"""

            # 5) Close this rule
            sld += "  </sld:Rule>\n"

    # Single-symbol styling
    else:
        sld += open_rule("Single symbol", scale_enabled, min_scale, max_scale)
        geom = style_data.get("geometry_type", "polygon")

        if geom == "point":
            sld += f"""\
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
            <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
          </sld:Stroke>
        </sld:Mark>
        <sld:Size>{point_size}</sld:Size>
      </sld:Graphic>
    </sld:PointSymbolizer>
"""
        elif geom == "line":
            sld += f"""\
    <sld:LineSymbolizer>
      <sld:Stroke>
        <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
        <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
        <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
      </sld:Stroke>
    </sld:LineSymbolizer>
"""
        else:  # polygon
            sld += f"""\
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

        # Label inside the single-symbol rule
        if label_enabled and label_field:
            sld += f"""\
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
          <sld:AnchorPointX>0.5</sld:AnchorPointX>
          <sld:AnchorPointY>0.5</sld:AnchorPointY>
        </sld:PointPlacement>
      </sld:LabelPlacement>
      <sld:Fill>
        <sld:CssParameter name="fill">{font_color}</sld:CssParameter>
      </sld:Fill>
    </sld:TextSymbolizer>
"""

        # Close single-symbol rule
        sld += "  </sld:Rule>\n"

    # SLD footer
    sld += """\
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
"""

    return sld



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