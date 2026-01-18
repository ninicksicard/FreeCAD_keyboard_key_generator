import csv
import os
from typing import List, Tuple

from copy import deepcopy
import FreeCAD as App

from keycap_exporter_core import (
    FACE_ROTATION,
    ExportConfiguration,
    build_keycap_with_legend_shape,
    export_stl, shape_to_mesh,
    resolve_object_by_name,
    FACE_DIRECTIONS,
    best_face_for_direction,
    ENGRAVING_DIRECTIONS,
    unit_vector,
)
from keycap_exporter_dialog import BatchKeycapDialog


def read_layout_entries(layout_file_path: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    with open(layout_file_path, newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            label_text = (row.get("primary") or "").strip()
            name_text = (row.get("name") or "").strip()
            if label_text:
                entries.append((label_text, name_text or label_text))
    return entries


def generate_keycaps_to_stl_from_selected_template() -> None:
    document = App.ActiveDocument
    if document is None:
        raise RuntimeError("No active document. Open your blank key document first.")

    dialog = BatchKeycapDialog(document)
    if dialog.exec_() != dialog.Accepted:
        App.Console.PrintMessage("Canceled.\n")
        return

    export_configuration: ExportConfiguration = dialog.get_configuration()

    if not export_configuration.font_path or not os.path.isfile(export_configuration.font_path):
        raise FileNotFoundError(f"Font file not found: {export_configuration.font_path}")

    if not export_configuration.output_directory:
        raise ValueError("Output folder is empty.")
    os.makedirs(export_configuration.output_directory, exist_ok=True)

    if not export_configuration.layout_file_path or not os.path.isfile(export_configuration.layout_file_path):
        raise FileNotFoundError(f"Layout file not found: {export_configuration.layout_file_path}")

    entries = read_layout_entries(export_configuration.layout_file_path)
    if len(entries) == 0:
        raise ValueError("Layout file has no primary labels.")

    App.Console.PrintMessage(f"Template: {export_configuration.template_object_name}\n")
    App.Console.PrintMessage(f"Face: {export_configuration.face_choice_label}\n")
    App.Console.PrintMessage(f"Font: {export_configuration.font_path}\n")
    App.Console.PrintMessage(f"Output: {export_configuration.output_directory}\n")
    App.Console.PrintMessage(f"Layout: {export_configuration.layout_file_path}\n")

    generate_configuration = deepcopy(export_configuration)

    template_object = resolve_object_by_name(document, generate_configuration.template_object_name)
    template_shape = template_object.Shape.copy()
    direction = FACE_DIRECTIONS[generate_configuration.face_choice_label]
    center = best_face_for_direction(template_shape, _direction=direction)
    face_placement = App.Placement(
        App.Vector(center.x, center.y, center.z),
        FACE_ROTATION[generate_configuration.face_choice_label],
        )

    if generate_configuration.mode == "engrave":
        extrusion_unit_vector = ENGRAVING_DIRECTIONS[generate_configuration.face_choice_label]
    else:
        extrusion_unit_vector = FACE_DIRECTIONS[generate_configuration.face_choice_label]
    extrusion_vector = unit_vector(extrusion_unit_vector).multiply(generate_configuration.depth_millimeter)
    for label_text, name_text in entries:
        final_solid = build_keycap_with_legend_shape(
            document=document,
            face_placement=face_placement,
            extrusion_vector=extrusion_vector,
            configuration=generate_configuration,
            blank_key=template_shape,
            label=label_text
            )
        mesh = shape_to_mesh(final_solid, generate_configuration.linear_deflection)
        output_path = os.path.join(generate_configuration.output_directory, f"{name_text}.stl")
        export_stl(mesh, output_path)
        App.Console.PrintMessage(f"Exported: {output_path}\n")

    App.Console.PrintMessage("Done.\n")
