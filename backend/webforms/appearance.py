"""Bounded design tokens shared by both public renderers."""

from rest_framework import serializers

FONTS = {
    "system": "system-ui, -apple-system, sans-serif",
    "arial": "Arial, Helvetica, sans-serif",
    "georgia": "Georgia, serif",
}
DEFAULTS = {
    "title": "",
    "description": "",
    "button_color": "#343234",
    "text_color": "#343234",
    "background_color": "#ffffff",
    "font": "system",
    "width": 640,
    "radius": 8,
    "columns": 1,
}


class AppearanceSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, allow_blank=True, required=False)
    description = serializers.CharField(
        max_length=500, allow_blank=True, required=False
    )
    button_color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    text_color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    background_color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    font = serializers.ChoiceField(choices=list(FONTS), required=False)
    width = serializers.IntegerField(min_value=280, max_value=1000, required=False)
    radius = serializers.IntegerField(min_value=0, max_value=24, required=False)
    columns = serializers.ChoiceField(choices=[1, 2], required=False)

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(DEFAULTS):
            raise serializers.ValidationError("Unsupported appearance setting.")
        return super().to_internal_value(data)


def form_appearance(form):
    # Validate again at the CSS boundary, including rows written outside the API.
    serializer = AppearanceSerializer(data=form.appearance or {})
    values = serializer.validated_data if serializer.is_valid() else {}
    result = {**DEFAULTS, **values}
    result["font_family"] = FONTS[result["font"]]
    color = result["button_color"].lstrip("#")
    channels = [int(color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    luminance = sum(c * w for c, w in zip(linear, [0.2126, 0.7152, 0.0722]))
    result["button_text_color"] = "#000000" if luminance > 0.179 else "#ffffff"
    return result
