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

    sld_body = generate_single_sld(style_data)

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

def _open_rule(rule_name, min_scale=None, max_scale=None):
    parts = [
        "<sld:Rule>",
        f"  <sld:Name>{rule_name}</sld:Name>"
    ]
    if min_scale is not None:
        parts.append(f"  <sld:MinScaleDenominator>{min_scale}</sld:MinScaleDenominator>")
    if max_scale is not None:
        parts.append(f"  <sld:MaxScaleDenominator>{max_scale}</sld:MaxScaleDenominator>")
    return "\n".join(parts) + "\n"

def _sld_header(layer_name, style_name):
    return f"""<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld"
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>{layer_name}</sld:Name>
    <sld:UserStyle>
      <sld:Name>{style_name}</sld:Name>
      <sld:FeatureTypeStyle>
"""

def _sld_footer():
    return """      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
"""

def _make_text_symbolizer(label_field, font_family, font_size, font_style, font_weight, font_color):
    """
    Returns a TextSymbolizer block given label parameters.
    """
    return f"""
  <sld:TextSymbolizer>
    <sld:Label>
      <ogc:PropertyName>{label_field}</ogc:PropertyName>
    </sld:Label>
    <sld:Font>
      <sld:CssParameter name=\"font-family\">{font_family}</sld:CssParameter>
      <sld:CssParameter name=\"font-size\">{font_size}</sld:CssParameter>
      <sld:CssParameter name=\"font-style\">{font_style}</sld:CssParameter>
      <sld:CssParameter name=\"font-weight\">{font_weight}</sld:CssParameter>
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
      <sld:CssParameter name=\"fill\">{font_color}</sld:CssParameter>
    </sld:Fill>
  </sld:TextSymbolizer>
"""

def generate_single_sld(style_data):
    """
    Generate an SLD with exactly one Rule, one symbolizer, and optional labeling.
    """
    layer = style_data.get("layer_name", "layer")
    style = style_data.get("name", "single_style")
    geom  = style_data.get("geometry_type", "polygon")

    # Symbol parameters
    stroke_color   = style_data.get("stroke_color", "#000000")
    stroke_width   = style_data.get("stroke_width", 1)
    stroke_opacity = style_data.get("stroke_opacity", 1)
    fill_color     = style_data.get("fill_color", "#FFFFFF")
    fill_opacity   = style_data.get("fill_opacity", 1)
    point_size     = style_data.get("point_size", 10)
    point_shape    = style_data.get("point_shape", "circle")

    # Label parameters
    label_enabled = style_data.get("label_enabled", False)
    label_field   = style_data.get("label_field")
    font_family   = style_data.get("font_family", "Arial")
    font_size     = style_data.get("font_size", 10)
    font_style    = style_data.get("font_style", "normal")
    font_weight   = style_data.get("font_weight", "normal")
    font_color    = style_data.get("font_color", "#000000")

    # Scale
    min_scale = style_data.get("min_scale_denominator")
    max_scale = style_data.get("max_scale_denominator")

    sld = _sld_header(layer, style)
    sld += _open_rule("Single symbol", min_scale, max_scale)

    # Symbolizer
    if geom == "point":
        sld += f"""
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
        sld += f"""
  <sld:LineSymbolizer>
    <sld:Stroke>
      <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
      <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
      <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
    </sld:Stroke>
  </sld:LineSymbolizer>
"""
    else:  # polygon
        sld += f"""
  <sld:PolygonSymbolizer>
    <sld:Fill>
      <sld:CssParameter name="fill">{fill_color}</sld:CssParameter>
      <sld:CssParameter name="fill-opacity">{fill_opacity}</sld:CssParameter>
    </sld:Fill>
    <sld:Stroke>
      <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
      <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
      <sld:CssParameter name="stroke-opacity">{stroke_opacity}</sld:CssParameter>
    </sld:Stroke>
  </sld:PolygonSymbolizer>
"""

    if label_enabled and label_field:
        sld += _make_text_symbolizer(
            label_field,
            font_family,
            font_size,
            font_style,
            font_weight,
            font_color
        )

    # Close rule and SLD
    sld += "  </sld:Rule>\n"
    sld += _sld_footer()

    return sld

def generate_rule_sld(style_data):
    """
    Generate an SLD with multiple Rules driven by a field,
    plus a fallback Rule for everything else.
    """
    if "field_name" not in style_data:
        raise ValueError("field_name is required for rule-based SLD")

    # Core identifiers
    layer         = style_data.get("layer_name", "layer")
    style         = style_data.get("name", "rule_style")
    field         = style_data["field_name"]
    base_geom     = style_data.get("geometry_type", "polygon")

    # Default symbol params
    stroke_op     = style_data.get("stroke_opacity", 1)
    fill_color    = style_data.get("fill_color", "#FFFFFF")
    fill_opacity  = style_data.get("fill_opacity", 1)
    stroke_color  = style_data.get("stroke_color", "#000000")
    stroke_width  = style_data.get("stroke_width", 1)
    point_size    = style_data.get("point_size", 10)
    point_shape   = style_data.get("point_shape", "circle")

    # Label params
    label_enabled = style_data.get("label_enabled", False)
    label_field   = style_data.get("label_field")
    font_family   = style_data.get("font_family", "Arial")
    font_size     = style_data.get("font_size", 10)
    font_style    = style_data.get("font_style", "normal")
    font_weight   = style_data.get("font_weight", "normal")
    font_color    = style_data.get("font_color", "#000000")

    sld = _sld_header(layer, style)

    # 1) explicit rules
    for rule in style_data.get("rules", []):
        name   = rule.get("name", "rule")
        val    = rule["value"]
        geom   = rule.get("geometry_type", base_geom)
        min_s  = rule.get("min_scale_denominator")
        max_s  = rule.get("max_scale_denominator")
        so     = rule.get("stroke_opacity", stroke_op)
        fc     = rule.get("fill_color", fill_color)
        fo     = rule.get("fill_opacity", fill_opacity)
        sc     = rule.get("stroke_color", stroke_color)
        sw     = rule.get("stroke_width", stroke_width)
        ps     = rule.get("point_size", point_size)
        shape  = rule.get("point_shape", point_shape)

        sld += _open_rule(name, min_s, max_s)
        sld += f"""
  <sld:Filter>
    <ogc:PropertyIsEqualTo>
      <ogc:PropertyName>{field}</ogc:PropertyName>
      <ogc:Literal>{val}</ogc:Literal>
    </ogc:PropertyIsEqualTo>
  </sld:Filter>
"""
        # symbolizer (same as before)…  
        if geom == "polygon":
            sld += f"""
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
            sld += f"""
  <sld:LineSymbolizer>
    <sld:Stroke>
      <sld:CssParameter name="stroke">{sc}</sld:CssParameter>
      <sld:CssParameter name="stroke-width">{sw}</sld:CssParameter>
      <sld:CssParameter name="stroke-opacity">{so}</sld:CssParameter>
    </sld:Stroke>
  </sld:LineSymbolizer>
"""
        else:  # point
            sld += f"""
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
        # label inside explicit rule  
        if label_enabled and label_field:
            sld += _make_text_symbolizer(
                label_field,
                font_family,
                font_size,
                font_style,
                font_weight,
                font_color
            )
        sld += "  </sld:Rule>\n"

    # 2) fallback rule for everything else (dedented outside the loop)
    sld += _open_rule(rule_name="default")
    
    sld += f"""
      <sld:Filter xmlns:ogc="http://www.opengis.net/ogc">
        <ogc:Or>
          <ogc:PropertyIsNull>
            <ogc:PropertyName>{field}</ogc:PropertyName>
          </ogc:PropertyIsNull>
          <ogc:PropertyIsEqualTo>
            <ogc:PropertyName>{field}</ogc:PropertyName>
            <ogc:Literal></ogc:Literal>
          </ogc:PropertyIsEqualTo>
        </ogc:Or>
      </sld:Filter>
    """

    # no <sld:Filter> here, so it catches all remaining features
    if base_geom == "polygon":
        sld += f"""
  <sld:PolygonSymbolizer>
    <sld:Fill>
      <sld:CssParameter name="fill">{fill_color}</sld:CssParameter>
      <sld:CssParameter name="fill-opacity">{fill_opacity}</sld:CssParameter>
    </sld:Fill>
    <sld:Stroke>
      <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
      <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
      <sld:CssParameter name="stroke-opacity">{stroke_op}</sld:CssParameter>
    </sld:Stroke>
  </sld:PolygonSymbolizer>
"""
    elif base_geom == "line":
        sld += f"""
  <sld:LineSymbolizer>
    <sld:Stroke>
      <sld:CssParameter name="stroke">{stroke_color}</sld:CssParameter>
      <sld:CssParameter name="stroke-width">{stroke_width}</sld:CssParameter>
      <sld:CssParameter name="stroke-opacity">{stroke_op}</sld:CssParameter>
    </sld:Stroke>
  </sld:LineSymbolizer>
"""
    else:  # point
        sld += f"""
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
          <sld:CssParameter name="stroke-opacity">{stroke_op}</sld:CssParameter>
        </sld:Stroke>
      </sld:Mark>
      <sld:Size>{point_size}</sld:Size>
    </sld:Graphic>
  </sld:PointSymbolizer>
"""
    # optional label on the fallback rule
    if label_enabled and label_field:
        sld += _make_text_symbolizer(
            label_field,
            font_family,
            font_size,
            font_style,
            font_weight,
            font_color
        )

    sld += "  </sld:Rule>\n"
    sld += _sld_footer()
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
        sld_body = generate_rule_sld(new_style_data)
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