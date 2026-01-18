import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import FreeCAD as App
import Draft
import Mesh
import Part

DEFAULT_FONT_DIRECTORIES: List[str] = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.local/share/fonts"),
    os.path.expanduser("~/.fonts"),
]

FACE_DIRECTIONS: Dict[str, App.Vector] = {
    "Top (+Z)": App.Vector(0.0, 0.0, 1.0),
    "Bottom (-Z)": App.Vector(0.0, 0.0, -1.0),
    "Front (+Y)": App.Vector(0.0, 1.0, 0.0),
    "Back (-Y)": App.Vector(0.0, -1.0, 0.0),
    "Right (+X)": App.Vector(1.0, 0.0, 0.0),
    "Left (-X)": App.Vector(-1.0, 0.0, 0.0),
}
ENGRAVING_DIRECTIONS: Dict[str, App.Vector] = {
    "Top (+Z)": App.Vector(0.0, 0.0, -1.0),
    "Bottom (-Z)": App.Vector(0.0, 0.0, 1.0),
    "Front (+Y)": App.Vector(0.0, -1.0, 0.0),
    "Back (-Y)": App.Vector(0.0, 1.0, 0.0),
    "Right (+X)": App.Vector(-1.0, 0.0, 0.0),
    "Left (-X)": App.Vector(1.0, 0.0, 0.0),
}
FACE_ROTATION: Dict[str, App.Rotation] = {
    # Assumed correct (identity): local axes = global axes
    # local X -> +X, local Y -> +Y, local Z -> +Z
    "Top (+Z)": App.Rotation(
        App.Vector(1.0, 0.0, 0.0),  # X
        App.Vector(0.0, 1.0, 0.0),  # Y
        App.Vector(0.0, 0.0, 1.0),  # Z
    ),

    # local Z -> -Z, keep local X -> +X (right-handed => local Y -> -Y)
    "Bottom (-Z)": App.Rotation(
        App.Vector(1.0, 0.0, 0.0),   # X
        App.Vector(0.0, -1.0, 0.0),  # Y
        App.Vector(0.0, 0.0, -1.0),  # Z
    ),

    # local Z -> +Y, choose local Y -> +Z (up on that face) => local X -> -X
    "Front (+Y)": App.Rotation(
        App.Vector(-1.0, 0.0, 0.0),  # X
        App.Vector(0.0, 0.0, 1.0),   # Y
        App.Vector(0.0, 1.0, 0.0),   # Z
    ),

    # local Z -> -Y, choose local Y -> +Z (up on that face) => local X -> +X
    "Back (-Y)": App.Rotation(
        App.Vector(1.0, 0.0, 0.0),   # X
        App.Vector(0.0, 0.0, 1.0),   # Y
        App.Vector(0.0, -1.0, 0.0),  # Z
    ),

    # local Z -> +X, choose local Y -> +Z (up on that face) => local X -> +Y
    "Right (+X)": App.Rotation(
        App.Vector(0.0, 1.0, 0.0),  # X
        App.Vector(0.0, 0.0, 1.0),  # Y
        App.Vector(1.0, 0.0, 0.0),  # Z
    ),

    # local Z -> -X, choose local Y -> +Z (up on that face) => local X -> -Y
    "Left (-X)": App.Rotation(
        App.Vector(0.0, -1.0, 0.0),  # X
        App.Vector(0.0, 0.0, 1.0),   # Y
        App.Vector(-1.0, 0.0, 0.0),  # Z
    ),
}




@dataclass(frozen=True)
class ExportConfiguration:
    template_object_name: str
    face_choice_label: str
    font_path: str
    output_directory: str
    layout_file_path: str
    mode: str
    primary_size_millimeter: float
    primary_offset_x_millimeter: float
    primary_offset_y_millimeter: float
    shift_size_millimeter: float
    shift_offset_x_millimeter: float
    shift_offset_y_millimeter: float
    depth_millimeter: float
    linear_deflection: float
    preview_label: str


def is_variable_font_filename(font_path: str) -> bool:
    base_name = os.path.basename(font_path).lower()
    return "variablefont" in base_name or "variable-font" in base_name


def scan_font_files(font_directories: List[str], include_variable_fonts: bool) -> List[str]:
    font_paths: List[str] = []
    for root_directory in font_directories:
        if not os.path.isdir(root_directory):
            continue
        for directory_path, _, filenames in os.walk(root_directory):
            for filename in filenames:
                lower_name = filename.lower()
                if not (lower_name.endswith(".ttf") or lower_name.endswith(".otf")):
                    continue
                full_path = os.path.join(directory_path, filename)
                if (not include_variable_fonts) and is_variable_font_filename(full_path):
                    continue
                font_paths.append(full_path)

    return sorted(set(font_paths), key=lambda font_path: font_path.lower())


def font_display_name(font_path: str) -> str:
    return os.path.basename(font_path)


def list_solid_objects(document: App.Document) -> List[App.DocumentObject]:
    result: List[App.DocumentObject] = []
    for document_object in document.Objects:
        if getattr(document_object, "Name", "") == "__KEYCAP_PREVIEW__":
            continue
        shape = getattr(document_object, "Shape", None)
        if shape is None:
            continue
        if shape.isNull():
            continue
        if len(shape.Solids) <= 0:
            continue
        result.append(document_object)
    return result


def object_display_name(document_object: App.DocumentObject) -> str:
    label = getattr(document_object, "Label", "") or ""
    name = getattr(document_object, "Name", "") or ""
    if label and name and label != name:
        return f"{label} ({name})"
    return label or name or "UnnamedObject"


def resolve_object_by_name(document: App.Document, name: str) -> App.DocumentObject:
    document_object = document.getObject(name)
    if document_object is None:
        raise ValueError(f"Selected template object not found: {name}")
    return document_object


def unit_vector(vector: App.Vector) -> App.Vector:
    if vector.Length == 0.0:
        raise ValueError("Zero-length vector.")
    return vector.multiply(1.0 / abs(vector.Length))


def best_face_for_direction(solid_shape: Part.Shape, _direction: App.Vector) -> Part.Face:

    best_center = _direction
    best_score = -1.0
    best_support = -1e100

    for face in solid_shape.Faces:
        u_middle = 0.5 * (face.ParameterRange[0] + face.ParameterRange[1])
        v_middle = 0.5 * (face.ParameterRange[2] + face.ParameterRange[3])
        normal = face.normalAt(u_middle, v_middle)

        _normal_vector = unit_vector(App.Vector(normal.x, normal.y, normal.z))
        score = _normal_vector.dot(_direction)
        if score < best_score:
            continue

        center = face.CenterOfMass
        support = App.Vector(center.x, center.y, center.z).dot(_direction)

        if (score > best_score + 1e-6) or (abs(score - best_score) <= 1e-6 and support > best_support):
            best_score = score
            best_support = support
            best_center = center

    return best_center

def shapestring_shape(document: App.Document, label: str, font_path: str, size_millimeter: float) -> Part.Shape:
    print(font_path)
    shapestring_object = Draft.makeShapeString(String=label, FontFile=font_path, Size=size_millimeter)
    shapestring_object.Label = f"temporary_shapestring_{label}"
    document.recompute()

    shape = shapestring_object.Shape.copy()
    document.removeObject(shapestring_object.Name)
    document.recompute()
    return shape


def extrude_to_solid(shape: Part.Shape, extrusion_vector: App.Vector) -> Part.Shape:
    if shape.ShapeType == "Wire":
        shape = Part.Face(shape)
    elif shape.ShapeType == "Compound":
        if len(shape.Faces) == 0 and len(shape.Wires) > 0:
            faces = [Part.Face(wire) for wire in shape.Wires]
            shape = Part.makeCompound(faces)

    return shape.extrude(extrusion_vector)


def shape_to_mesh(shape: Part.Shape, linear_deflection: float) -> "Mesh.Mesh":
    if linear_deflection <= 0.0:
        raise ValueError("Linear deflection must be > 0.")
    mesh = Mesh.Mesh()
    triangles = shape.tessellate(linear_deflection)
    mesh.addFacets(triangles)
    return mesh


def export_stl(mesh: "Mesh.Mesh", filepath: str) -> None:
    mesh.write(filepath)


def remove_existing_preview(document: App.Document) -> None:
    preview_object = document.getObject("__KEYCAP_PREVIEW__")
    if preview_object is not None:
        document.removeObject(preview_object.Name)
        document.recompute()


def set_preview_shape(document: App.Document, shape: Part.Shape) -> None:
    preview_object = document.getObject("__KEYCAP_PREVIEW__")
    if preview_object is None:
        preview_object = document.addObject("Part::Feature", "__KEYCAP_PREVIEW__")
        preview_object.Label = "__KEYCAP_PREVIEW__"
    preview_object.Shape = shape
    document.recompute()


def build_keycap_with_legend_shape(
        document: App.Document,
        face_placement,
        extrusion_vector,
        configuration: ExportConfiguration,
        blank_key,
        label: str,
        shift_label: str,
) -> Part.Shape:
    def build_legend_shape(legend_label: str, size_millimeter: float, offset_x: float, offset_y: float) -> Part.Shape:
        legend_shape = shapestring_shape(document, legend_label, configuration.font_path, size_millimeter)
        bounding_box = legend_shape.BoundBox
        legend_center_x = (bounding_box.XMin + bounding_box.XMax) * 0.5
        legend_center_y = (bounding_box.YMin + bounding_box.YMax) * 0.5
        legend_shape.translate(App.Vector(-legend_center_x, -legend_center_y, 0.0))
        legend_shape.translate(App.Vector(offset_x, offset_y, 0.0))
        legend_shape.Placement = face_placement.multiply(legend_shape.Placement)
        return legend_shape

    primary_offset_x = 0.0
    primary_offset_y = 0.0
    if shift_label:
        primary_offset_x = configuration.primary_offset_x_millimeter
        primary_offset_y = configuration.primary_offset_y_millimeter

    legend_shapes = [
        build_legend_shape(
            legend_label=label,
            size_millimeter=configuration.primary_size_millimeter,
            offset_x=primary_offset_x,
            offset_y=primary_offset_y,
        )
    ]
    if shift_label:
        legend_shapes.append(
            build_legend_shape(
                legend_label=shift_label,
                size_millimeter=configuration.shift_size_millimeter,
                offset_x=configuration.shift_offset_x_millimeter,
                offset_y=configuration.shift_offset_y_millimeter,
            )
        )

    legend_solid = None
    for legend_shape in legend_shapes:
        legend_solid_piece = extrude_to_solid(legend_shape, extrusion_vector)
        if legend_solid is None:
            legend_solid = legend_solid_piece
        else:
            legend_solid = legend_solid.fuse(legend_solid_piece)

    if legend_solid is None:
        raise ValueError("Legend shape creation failed.")

    if configuration.mode == "raise":
        return blank_key.fuse(legend_solid)
    if configuration.mode == "engrave":
        return blank_key.cut(legend_solid)

    raise ValueError('Legend mode must be "engrave" or "raise".')
