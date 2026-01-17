import os
from typing import List, Tuple

import FreeCAD as App

from keycap_exporter_core import ExportConfiguration, build_keycap_with_legend_shape, export_stl, shape_to_mesh
from keycap_exporter_dialog import BatchKeycapDialog


def generate_keycaps_to_stl_from_selected_template(keys: List[Tuple[str, str]]) -> None:
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

    App.Console.PrintMessage(f"Template: {export_configuration.template_object_name}\n")
    App.Console.PrintMessage(f"Face: {export_configuration.face_choice_label}\n")
    App.Console.PrintMessage(f"Font: {export_configuration.font_path}\n")
    App.Console.PrintMessage(f"Output: {export_configuration.output_directory}\n")

    for label, safe_name in keys:
        final_solid = build_keycap_with_legend_shape(document, export_configuration, label=label)
        mesh = shape_to_mesh(final_solid, export_configuration.linear_deflection)
        output_path = os.path.join(export_configuration.output_directory, f"{safe_name}.stl")
        export_stl(mesh, output_path)
        App.Console.PrintMessage(f"Exported: {output_path}\n")

    App.Console.PrintMessage("Done.\n")
