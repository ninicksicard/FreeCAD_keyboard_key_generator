"""Preview object helpers."""


def remove_existing_preview(doc):
    obj = doc.getObject("__KEYCAP_PREVIEW__")
    if obj is not None:
        doc.removeObject(obj.Name)
        doc.recompute()


def set_preview_shape(doc, shape):
    obj = doc.getObject("__KEYCAP_PREVIEW__")
    if obj is None:
        obj = doc.addObject("Part::Feature", "__KEYCAP_PREVIEW__")
        obj.Label = "__KEYCAP_PREVIEW__"
    obj.Shape = shape
    doc.recompute()
