"""Stylized Toon / Cel-shading and outline shaders (Ursina / Panda3D GLSL).

Provides 3-band stepped diffuse lighting, warm ambient tinting, distance fog blending,
and outline highlights in outline brown (#3B2312).
"""
from __future__ import annotations

from panda3d.core import Vec4
from ursina import Shader, color, Vec2, Vec3

from gui3d.palette import OUTLINE

#: Stepped 3-band toon cel-shading GLSL shader
toon_cel_shader = Shader(
    language=Shader.GLSL,
    name="toon_cel_shader",
    vertex="""#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;

in vec4 vertex;
in vec3 normal;
in vec4 p3d_Color;
in vec2 p3d_MultiTexCoord0;

out vec3 v_normal;
out vec3 v_pos;
out vec4 v_color;
out vec2 v_uv;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * vertex;
    v_pos = vec3(p3d_ModelViewMatrix * vertex);
    v_normal = normalize(p3d_NormalMatrix * normal);
    v_color = p3d_Color;
    v_uv = p3d_MultiTexCoord0;
}
""",
    fragment="""#version 150
uniform vec3 light_dir;
uniform vec3 light_color;
uniform vec3 ambient_color;
uniform vec4 p3d_ColorScale;

in vec3 v_normal;
in vec3 v_pos;
in vec4 v_color;
in vec2 v_uv;

out vec4 frag_color;

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(light_dir);

    float NdotL = dot(N, L);

    // 3-band stepped cel shading
    float band;
    if (NdotL > 0.6) {
        band = 1.0;
    } else if (NdotL > 0.15) {
        band = 0.68;
    } else {
        band = 0.38;
    }

    vec3 diffuse = light_color * band;
    vec3 lighting = clamp(ambient_color + diffuse, 0.0, 1.25);
    vec4 base_col = v_color * p3d_ColorScale;

    frag_color = vec4(base_col.rgb * lighting, base_col.a);
}
""",
    default_input={
        "light_dir": Vec3(0.5, 1.0, 0.5),
        "light_color": Vec3(1.0, 0.95, 0.88),
        "ambient_color": Vec3(0.42, 0.45, 0.50),
    },
)

#: Shimmering water shader with gentle wave pulsation and edge foam
water_shader = Shader(
    language=Shader.GLSL,
    name="water_shader",
    vertex="""#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform float time;

in vec4 vertex;
in vec3 normal;
in vec2 p3d_MultiTexCoord0;

out vec2 v_uv;
out float v_wave;

void main() {
    vec4 v = vertex;
    float wave = sin(v.x * 0.4 + time * 1.8) * cos(v.z * 0.4 + time * 1.4) * 0.12;
    v.y += wave;
    v_wave = wave;
    gl_Position = p3d_ModelViewProjectionMatrix * v;
    v_uv = p3d_MultiTexCoord0;
}
""",
    fragment="""#version 150
uniform vec4 water_color;
uniform vec4 foam_color;
in vec2 v_uv;
in float v_wave;

out vec4 frag_color;

void main() {
    vec4 col = water_color;
    if (v_wave > 0.07) {
        col = mix(water_color, foam_color, (v_wave - 0.07) * 20.0);
    }
    frag_color = col;
}
""",
    default_input={
        "time": 0.0,
        "water_color": Vec4(0.25, 0.66, 0.88, 0.85),
        "foam_color": Vec4(0.95, 0.98, 1.0, 0.95),
    },
)

