"""STL export pipeline."""

import os
import sys

import FreeCAD as App
from PySide2 import QtWidgets

from batch_keycaps_export_stl_ui import core
from batch_keycaps_export_stl_ui import geometry_utils
from batch_keycaps_export_stl_ui import ui


def generate_keycaps_to_stl_from_selected_template(keys):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active document. Open your blank key document first.")

    dialog = ui.BatchKeycapDialog(doc)
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        App.Console.PrintMessage("Canceled.\n")
        return

    cfg = dialog.get_config()

    if not cfg.font_path or not os.path.isfile(cfg.font_path):
        raise FileNotFoundError("Font file not found: %s" % cfg.font_path)

    if not cfg.output_dir:
        raise ValueError("Output folder is empty.")
    os.makedirs(cfg.output_dir, exist_ok=True)

    App.Console.PrintMessage("Template: %s\n" % cfg.template_object_name)
    App.Console.PrintMessage("Face: %s\n" % cfg.face_choice_label)
    App.Console.PrintMessage("Font: %s\n" % cfg.font_path)
    App.Console.PrintMessage("Output: %s\n" % cfg.output_dir)

    face_directions = sys.modules["main"].FACE_DIRECTIONS
    for label, safe_name in keys:
        final_solid = core.build_keycap_with_legend_shape(
            doc, cfg, label=label, face_directions=face_directions
        )
        mesh = geometry_utils.shape_to_mesh(final_solid, cfg.linear_deflection)
        out_path = os.path.join(cfg.output_dir, "%s.stl" % safe_name)
        geometry_utils.export_stl(mesh, out_path)
        App.Console.PrintMessage("Exported: %s\n" % out_path)

    App.Console.PrintMessage("Done.\n")
