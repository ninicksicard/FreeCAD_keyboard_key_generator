import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import FreeCAD as App
import Draft
import Mesh
import Part


KEYS_TO_EXPORT: List[Tuple[str, str]] = [
    ("ESC", "ESC"),
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
    ("Q", "Q"),
    ("W", "W"),
    ("E", "E"),
    ("A", "A"),
    ("S", "S"),
    ("D", "D"),
    ("Z", "Z"),
    ("X", "X"),
    ("C", "C"),
    ("SPACE", "SPACE"),
]

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


@dataclass(frozen=True)
class ExportConfiguration:
    template_object_name: str
    face_choice_label: str
    font_path: str
    output_directory: str
    mode: str
    size_millimeter: float
    depth_millimeter: float
    offset_x_millimeter: float
    offset_y_millimeter: float
    extrusion_vector_x: float
    extrusion_vector_y: float
    extrusion_vector_z: float
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
    return vector.multiply(1.0 / vector.Length)


def best_face_for_direction(solid_shape: Part.Shape, direction_world: App.Vector) -> Part.Face:
    direction = unit_vector(direction_world)

    best_face: Optional[Part.Face] = None
    best_score = -1.0
    best_support = -1e100

    for face in solid_shape.Faces:
        u_middle = 0.5 * (face.ParameterRange[0] + face.ParameterRange[1])
        v_middle = 0.5 * (face.ParameterRange[2] + face.ParameterRange[3])
        normal = face.normalAt(u_middle, v_middle)

        normal_vector = unit_vector(App.Vector(normal.x, normal.y, normal.z))
        score = normal_vector.dot(direction)
        if score < best_score:
            continue

        center = face.CenterOfMass
        support = App.Vector(center.x, center.y, center.z).dot(direction)

        if (score > best_score + 1e-6) or (abs(score - best_score) <= 1e-6 and support > best_support):
            best_face = face
            best_score = score
            best_support = support

    if best_face is None:
        raise RuntimeError("Could not determine a suitable face for the selected direction.")
    return best_face


def face_plane_placement(face: Part.Face) -> Tuple[App.Placement, App.Vector]:
    center = face.CenterOfMass
    u_middle = 0.5 * (face.ParameterRange[0] + face.ParameterRange[1])
    v_middle = 0.5 * (face.ParameterRange[2] + face.ParameterRange[3])
    normal = face.normalAt(u_middle, v_middle)
    normal_vector = unit_vector(App.Vector(normal.x, normal.y, normal.z))

    up = App.Vector(0.0, 0.0, 1.0)
    if abs(normal_vector.dot(up)) > 0.95:
        up = App.Vector(0.0, 1.0, 0.0)

    x_axis = unit_vector(up.cross(normal_vector))
    y_axis = unit_vector(normal_vector.cross(x_axis))

    rotation = App.Rotation(x_axis, y_axis, normal_vector)
    placement = App.Placement(App.Vector(center.x, center.y, center.z), rotation)
    return placement, normal_vector


def shapestring_shape(document: App.Document, label: str, font_path: str, size_millimeter: float) -> Part.Shape:
    shapestring_object = Draft.makeShapeString(String=label, FontFile=font_path, Size=size_millimeter)
    shapestring_object.Label = f"temporary_shapestring_{label}"
    document.recompute()

    shape = shapestring_object.Shape.copy()
    document.removeObject(shapestring_object.Name)
    document.recompute()
    return shape


def extrude_to_solid(shape: Part.Shape, height_millimeter: float, extrusion_vector: App.Vector) -> Part.Shape:
    if extrusion_vector.Length <= 0.0:
        if height_millimeter <= 0.0:
            raise ValueError("Legend height or depth must be > 0.")
        extrusion_vector = App.Vector(0.0, 0.0, height_millimeter)

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
    export_configuration: ExportConfiguration,
    label: str,
) -> Part.Shape:
    template_object = resolve_object_by_name(document, export_configuration.template_object_name)
    template_shape = template_object.Shape.copy()
    if template_shape.isNull() or len(template_shape.Solids) <= 0:
        raise RuntimeError("Template object does not contain a solid. Pick a Body or feature that is the final solid.")

    direction = FACE_DIRECTIONS.get(export_configuration.face_choice_label)
    if direction is None:
        raise ValueError(f"Unknown face choice: {export_configuration.face_choice_label}")

    face = best_face_for_direction(template_shape, direction_world=direction)
    face_placement, _ = face_plane_placement(face)

    legend_shape = shapestring_shape(document, label, export_configuration.font_path, export_configuration.size_millimeter)

    bounding_box = legend_shape.BoundBox
    legend_center_x = (bounding_box.XMin + bounding_box.XMax) * 0.5
    legend_center_y = (bounding_box.YMin + bounding_box.YMax) * 0.5

    legend_shape.translate(App.Vector(-legend_center_x, -legend_center_y, 0.0))
    legend_shape.translate(
        App.Vector(export_configuration.offset_x_millimeter, export_configuration.offset_y_millimeter, 0.0)
    )

    overlap = 0.05
    legend_shape.translate(App.Vector(0.0, 0.0, -overlap))
    legend_shape.Placement = face_placement.multiply(legend_shape.Placement)

    legend_solid = extrude_to_solid(
        legend_shape,
        export_configuration.depth_millimeter,
        App.Vector(
            export_configuration.extrusion_vector_x,
            export_configuration.extrusion_vector_y,
            export_configuration.extrusion_vector_z,
        ),
    )

    blank_key = template_shape.copy()

    if export_configuration.mode == "raise":
        return blank_key.fuse(legend_solid)
    if export_configuration.mode == "engrave":
        return blank_key.cut(legend_solid)

    raise ValueError('Legend mode must be "engrave" or "raise".')
