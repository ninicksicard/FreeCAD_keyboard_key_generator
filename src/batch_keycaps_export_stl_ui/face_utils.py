"""Face selection and placement helpers."""

import FreeCAD as App


def unit_vector(vector):
    if vector.Length == 0.0:
        raise ValueError("Zero-length vector.")
    return vector.multiply(1.0 / vector.Length)


def best_face_for_direction(solid_shape, direction_world):
    """
    Pick the face whose normal best matches direction_world.
    Uses face normal at face center.
    """
    direction = unit_vector(direction_world)

    best_face = None
    best_score = -1.0
    best_support = -1e100

    for face in solid_shape.Faces:
        try:
            u_mid = 0.5 * (face.ParameterRange[0] + face.ParameterRange[1])
            v_mid = 0.5 * (face.ParameterRange[2] + face.ParameterRange[3])
            normal = face.normalAt(u_mid, v_mid)
        except Exception:
            continue

        normal_vector = unit_vector(App.Vector(normal.x, normal.y, normal.z))
        score = normal_vector.dot(direction)
        if score < best_score:
            continue

        center = face.CenterOfMass
        support = App.Vector(center.x, center.y, center.z).dot(direction)

        if (score > best_score + 1e-6) or (
            abs(score - best_score) <= 1e-6 and support > best_support
        ):
            best_face = face
            best_score = score
            best_support = support

    if best_face is None:
        raise RuntimeError("Could not determine a suitable face for the selected direction.")
    return best_face


def make_face_plane_placement(face):
    """
    Build a local coordinate system for the face:
    - origin at face center of mass
    - Z axis = face normal
    - X/Y axes = arbitrary but stable basis on the face plane
    Returns:
    - placement mapping local -> world
    - face_normal (world unit)
    """
    center = face.CenterOfMass
    u_mid = 0.5 * (face.ParameterRange[0] + face.ParameterRange[1])
    v_mid = 0.5 * (face.ParameterRange[2] + face.ParameterRange[3])
    normal = face.normalAt(u_mid, v_mid)
    normal_vector = unit_vector(App.Vector(normal.x, normal.y, normal.z))

    up = App.Vector(0.0, 0.0, 1.0)
    if abs(normal_vector.dot(up)) > 0.95:
        up = App.Vector(0.0, 1.0, 0.0)

    x_axis = unit_vector(up.cross(normal_vector))
    y_axis = unit_vector(normal_vector.cross(x_axis))

    rotation = App.Rotation(x_axis, y_axis, normal_vector)
    placement = App.Placement(App.Vector(center.x, center.y, center.z), rotation)
    return placement, normal_vector
