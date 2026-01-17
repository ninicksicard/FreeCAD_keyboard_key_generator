"""Configuration objects."""


class ExportConfig:
    def __init__(
        self,
        template_object_name,
        face_choice_label,
        font_path,
        output_dir,
        mode,
        size_mm,
        depth_mm,
        offset_x_mm,
        offset_y_mm,
        linear_deflection,
        preview_label,
    ):
        self.template_object_name = template_object_name
        self.face_choice_label = face_choice_label
        self.font_path = font_path
        self.output_dir = output_dir
        self.mode = mode
        self.size_mm = size_mm
        self.depth_mm = depth_mm
        self.offset_x_mm = offset_x_mm
        self.offset_y_mm = offset_y_mm
        self.linear_deflection = linear_deflection
        self.preview_label = preview_label
