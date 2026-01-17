"""Shape building helpers."""

import FreeCAD as App
import Draft
import Mesh
import Part


def make_shapestring_shape(doc, label, font_path, size_mm):
    shapestring_obj = Draft.makeShapeString(String=label, FontFile=font_path, Size=size_mm)
    shapestring_obj.Label = "tmp_shapestring_%s" % label
    doc.recompute()

    shape = shapestring_obj.Shape.copy()
    doc.removeObject(shapestring_obj.Name)
    doc.recompute()
    return shape


def extrude_to_solid(shape, height_mm):
    if height_mm <= 0.0:
        raise ValueError("Legend height/depth must be > 0.")

    if shape.ShapeType == "Wire":
        shape = Part.Face(shape)
    elif shape.ShapeType == "Compound":
        if len(shape.Faces) == 0 and len(shape.Wires) > 0:
            faces = []
            for wire in shape.Wires:
                faces.append(Part.Face(wire))
            shape = Part.makeCompound(faces)

    return shape.extrude(App.Vector(0.0, 0.0, height_mm))


def shape_to_mesh(shape, linear_deflection):
    if linear_deflection <= 0.0:
        raise ValueError("Linear deflection must be > 0.")
    mesh = Mesh.Mesh()
    triangles = shape.tessellate(linear_deflection)
    mesh.addFacets(triangles)
    return mesh


def export_stl(mesh, filepath):
    mesh.write(filepath)
