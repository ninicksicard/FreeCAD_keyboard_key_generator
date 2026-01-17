"""FreeCAD document object helpers."""

import FreeCAD as App


def list_solid_objects(doc):
    result = []
    for obj in doc.Objects:
        if not hasattr(obj, "Shape"):
            continue
        try:
            shape = obj.Shape
        except Exception:
            continue
        if shape is None or shape.isNull():
            continue
        if len(shape.Solids) <= 0:
            continue
        result.append(obj)
    return result


def object_display_name(obj):
    label = getattr(obj, "Label", "") or ""
    name = getattr(obj, "Name", "") or ""
    if label and name and label != name:
        return "%s (%s)" % (label, name)
    return label or name or "UnnamedObject"


def resolve_object_by_name(doc, name):
    obj = doc.getObject(name)
    if obj is None:
        raise ValueError("Selected template object not found: %s" % name)
    return obj
