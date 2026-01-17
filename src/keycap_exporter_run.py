import csv
import os
from typing import List

import FreeCAD as App

from keycap_exporter_core import ExportConfiguration, build_keycap_with_legend_shape, export_stl, shape_to_mesh
from keycap_exporter_dialog import BatchKeycapDialog


def read_primary_labels(layout_file_path: str) -> List[str]:
    labels: List[str] = []
    with open(layout_file_path, newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            primary_label = (row.get("primary") or "").strip()
            if primary_label:
                labels.append(primary_label)
    return labels


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

    labels = read_primary_labels(export_configuration.layout_file_path)
    if len(labels) == 0:
        raise ValueError("Layout file has no primary labels.")

    App.Console.PrintMessage(f"Template: {export_configuration.template_object_name}\n")
    App.Console.PrintMessage(f"Face: {export_configuration.face_choice_label}\n")
    App.Console.PrintMessage(f"Font: {export_configuration.font_path}\n")
    App.Console.PrintMessage(f"Output: {export_configuration.output_directory}\n")
    App.Console.PrintMessage(f"Layout: {export_configuration.layout_file_path}\n")

    for label in labels:
        final_solid = build_keycap_with_legend_shape(document, export_configuration, label=label)
        mesh = shape_to_mesh(final_solid, export_configuration.linear_deflection)
        output_path = os.path.join(export_configuration.output_directory, f"{label}.stl")
        export_stl(mesh, output_path)
        App.Console.PrintMessage(f"Exported: {output_path}\n")

    App.Console.PrintMessage("Done.\n")
