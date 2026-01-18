import os
from copy import deepcopy
import FreeCAD as App

from keycap_exporter_core import (
    ExportConfiguration,
    build_keycap_shape_from_configuration,
    export_stl, shape_to_mesh,
    read_layout_entries,
    resolve_object_by_name,
)
from keycap_exporter_dialog import BatchKeycapDialog


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
    for label_text, shift_text, altcr_text, name_text in entries:
        final_solid = build_keycap_shape_from_configuration(
            document,
            template_shape,
            generate_configuration,
            label_text,
            shift_text or None,
            altcr_text or None,
        )
        mesh = shape_to_mesh(final_solid, generate_configuration.linear_deflection)
        output_path = os.path.join(generate_configuration.output_directory, f"{name_text}.stl")
        export_stl(mesh, output_path)
        App.Console.PrintMessage(f"Exported: {output_path}\n")

    App.Console.PrintMessage("Done.\n")
