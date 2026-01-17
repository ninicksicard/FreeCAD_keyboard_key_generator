"""Core legend build pipeline."""

import FreeCAD as App

from batch_keycaps_export_stl_ui import face_utils
from batch_keycaps_export_stl_ui import geometry_utils
from batch_keycaps_export_stl_ui import object_utils


def build_keycap_with_legend_shape(doc, cfg, label, face_directions):
    template_obj = object_utils.resolve_object_by_name(doc, cfg.template_object_name)
    template_shape = template_obj.Shape.copy()
    if template_shape.isNull() or len(template_shape.Solids) <= 0:
        raise RuntimeError(
            "Template object does not contain a solid. Pick a Body/feature that is the final solid."
        )

    direction = face_directions.get(cfg.face_choice_label)
    if direction is None:
        raise ValueError("Unknown face choice: %s" % cfg.face_choice_label)

    face = face_utils.best_face_for_direction(template_shape, direction_world=direction)
    face_placement, _face_normal = face_utils.make_face_plane_placement(face)

    legend_shape = geometry_utils.make_shapestring_shape(doc, label, cfg.font_path, cfg.size_mm)

    legend_bbox = legend_shape.BoundBox
    legend_center_x = (legend_bbox.XMin + legend_bbox.XMax) * 0.5
    legend_center_y = (legend_bbox.YMin + legend_bbox.YMax) * 0.5

    legend_shape.translate(App.Vector(-legend_center_x, -legend_center_y, 0.0))
    legend_shape.translate(App.Vector(cfg.offset_x_mm, cfg.offset_y_mm, 0.0))

    overlap = 0.05
    legend_shape.translate(App.Vector(0.0, 0.0, -overlap))
    legend_shape.Placement = face_placement.multiply(legend_shape.Placement)

    legend_solid = geometry_utils.extrude_to_solid(legend_shape, cfg.depth_mm)

    blank_key = template_shape.copy()

    if cfg.mode == "raise":
        final_solid = blank_key.fuse(legend_solid)
    elif cfg.mode == "engrave":
        final_solid = blank_key.cut(legend_solid)
    else:
        raise ValueError('Legend mode must be "engrave" or "raise".')

    return final_solid
