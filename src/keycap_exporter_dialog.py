import csv
import json
import os
from typing import Dict, List

import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from keycap_exporter_core import (
    DEFAULT_FONT_DIRECTORIES,
    FACE_DIRECTIONS,
    ExportConfiguration,
    build_keycap_shape_from_configuration,
    font_display_name,
    is_variable_font_filename,
    list_solid_objects,
    object_display_name,
    remove_existing_preview,
    read_layout_entries,
    scan_font_files,
    set_preview_shape,
    resolve_object_by_name,
)


class BatchKeycapDialog(QtWidgets.QDialog):
    def __init__(self, document: App.Document) -> None:
        super().__init__(Gui.getMainWindow())
        self.setWindowTitle("Batch Keycap STL Export")

        self.document = document

        self.solid_objects = list_solid_objects(document)

        self.template_selector = QtWidgets.QComboBox()
        self.template_name_by_index: Dict[int, str] = {}
        for index, document_object in enumerate(self.solid_objects):
            self.template_selector.addItem(object_display_name(document_object))
            self.template_name_by_index[index] = document_object.Name

        self.face_selector = QtWidgets.QComboBox()
        for face_label in FACE_DIRECTIONS.keys():
            self.face_selector.addItem(face_label)

        self.include_variable_fonts_checkbox = QtWidgets.QCheckBox("Include variable fonts")
        self.include_variable_fonts_checkbox.setChecked(False)
        self.include_variable_fonts_checkbox.stateChanged.connect(self.reload_fonts)

        self.font_selector = QtWidgets.QComboBox()
        self.font_paths: List[str] = []
        self.font_path_by_index: Dict[int, str] = {}

        self.font_browse_button = QtWidgets.QPushButton("Browse...")
        self.font_browse_button.clicked.connect(self.browse_font)

        self.output_directory_edit = QtWidgets.QLineEdit(os.path.expanduser("~/keycaps_stl_out"))
        self.output_browse_button = QtWidgets.QPushButton("Browse...")
        self.output_browse_button.clicked.connect(self.browse_output_directory)

        self.layout_file_edit = QtWidgets.QLineEdit("")
        self.layout_browse_button = QtWidgets.QPushButton("Browse...")
        self.layout_browse_button.clicked.connect(self.browse_layout_file)

        self.theme_file_edit = QtWidgets.QLineEdit("")
        self.theme_load_button = QtWidgets.QPushButton("Load theme...")
        self.theme_save_button = QtWidgets.QPushButton("Save theme...")
        self.theme_load_button.clicked.connect(self.load_theme)
        self.theme_save_button.clicked.connect(self.save_theme)

        self.mode_selector = QtWidgets.QComboBox()
        self.mode_selector.addItems(["engrave", "raise"])

        self.shift_enabled_checkbox = QtWidgets.QCheckBox("Enable Shift legend")
        self.shift_enabled_checkbox.setChecked(True)

        self.alternate_graphic_enabled_checkbox = QtWidgets.QCheckBox("Enable AltGr legend")
        self.alternate_graphic_enabled_checkbox.setChecked(True)

        self.function_enabled_checkbox = QtWidgets.QCheckBox("Enable Fn legend")
        self.function_enabled_checkbox.setChecked(True)

        self.primary_font_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.primary_font_size_spin_box.setRange(1.0, 50.0)
        self.primary_font_size_spin_box.setDecimals(2)
        self.primary_font_size_spin_box.setValue(6.0)

        self.shift_font_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.shift_font_size_spin_box.setRange(1.0, 50.0)
        self.shift_font_size_spin_box.setDecimals(2)
        self.shift_font_size_spin_box.setValue(4.0)

        self.altcr_font_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.altcr_font_size_spin_box.setRange(1.0, 50.0)
        self.altcr_font_size_spin_box.setDecimals(2)
        self.altcr_font_size_spin_box.setValue(4.0)

        self.function_font_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.function_font_size_spin_box.setRange(1.0, 50.0)
        self.function_font_size_spin_box.setDecimals(2)
        self.function_font_size_spin_box.setValue(4.0)

        self.depth_spin_box = QtWidgets.QDoubleSpinBox()
        self.depth_spin_box.setRange(0.05, 10.0)
        self.depth_spin_box.setDecimals(2)
        self.depth_spin_box.setValue(0.6)

        self.primary_offset_x_spin_box = QtWidgets.QDoubleSpinBox()
        self.primary_offset_x_spin_box.setRange(-50.0, 50.0)
        self.primary_offset_x_spin_box.setDecimals(2)
        self.primary_offset_x_spin_box.setValue(-2.0)

        self.primary_offset_y_spin_box = QtWidgets.QDoubleSpinBox()
        self.primary_offset_y_spin_box.setRange(-50.0, 50.0)
        self.primary_offset_y_spin_box.setDecimals(2)
        self.primary_offset_y_spin_box.setValue(0.0)

        self.shift_offset_x_spin_box = QtWidgets.QDoubleSpinBox()
        self.shift_offset_x_spin_box.setRange(-50.0, 50.0)
        self.shift_offset_x_spin_box.setDecimals(2)
        self.shift_offset_x_spin_box.setValue(2.0)

        self.shift_offset_y_spin_box = QtWidgets.QDoubleSpinBox()
        self.shift_offset_y_spin_box.setRange(-50.0, 50.0)
        self.shift_offset_y_spin_box.setDecimals(2)
        self.shift_offset_y_spin_box.setValue(2.0)

        self.altcr_offset_x_spin_box = QtWidgets.QDoubleSpinBox()
        self.altcr_offset_x_spin_box.setRange(-50.0, 50.0)
        self.altcr_offset_x_spin_box.setDecimals(2)
        self.altcr_offset_x_spin_box.setValue(2.0)

        self.altcr_offset_y_spin_box = QtWidgets.QDoubleSpinBox()
        self.altcr_offset_y_spin_box.setRange(-50.0, 50.0)
        self.altcr_offset_y_spin_box.setDecimals(2)
        self.altcr_offset_y_spin_box.setValue(-2.0)

        self.function_offset_x_spin_box = QtWidgets.QDoubleSpinBox()
        self.function_offset_x_spin_box.setRange(-50.0, 50.0)
        self.function_offset_x_spin_box.setDecimals(2)
        self.function_offset_x_spin_box.setValue(0.0)

        self.function_offset_y_spin_box = QtWidgets.QDoubleSpinBox()
        self.function_offset_y_spin_box.setRange(-50.0, 50.0)
        self.function_offset_y_spin_box.setDecimals(2)
        self.function_offset_y_spin_box.setValue(-2.0)

        self.linear_deflection_spin_box = QtWidgets.QDoubleSpinBox()
        self.linear_deflection_spin_box.setRange(0.01, 2.0)
        self.linear_deflection_spin_box.setDecimals(3)
        self.linear_deflection_spin_box.setValue(0.08)

        self.preview_label_edit = QtWidgets.QLineEdit("A")
        self.preview_update_button = QtWidgets.QPushButton("Update Preview")
        self.preview_clear_button = QtWidgets.QPushButton("Clear Preview")

        self.preview_update_button.clicked.connect(self.update_preview_clicked)
        self.preview_clear_button.clicked.connect(self.clear_preview_clicked)

        self.reload_fonts()
        self.generate_configuration = self.get_configuration_for_preview()
        form_layout = QtWidgets.QFormLayout()

        if len(self.solid_objects) == 0:
            warning_label = QtWidgets.QLabel(
                "No solid template objects found in this document (need Shape with Solids)."
            )
            warning_label.setStyleSheet("color: #cc0000;")
            form_layout.addRow("Template:", warning_label)
        else:
            form_layout.addRow("Template object:", self.template_selector)

        form_layout.addRow("Legend face:", self.face_selector)

        font_row = QtWidgets.QHBoxLayout()
        font_row.addWidget(self.font_selector)
        font_row.addWidget(self.font_browse_button)
        form_layout.addRow("Font:", font_row)
        form_layout.addRow("", self.include_variable_fonts_checkbox)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.output_directory_edit)
        output_row.addWidget(self.output_browse_button)
        form_layout.addRow("Output folder:", output_row)

        layout_row = QtWidgets.QHBoxLayout()
        layout_row.addWidget(self.layout_file_edit)
        layout_row.addWidget(self.layout_browse_button)
        form_layout.addRow("Layout file:", layout_row)

        theme_row = QtWidgets.QHBoxLayout()
        theme_row.addWidget(self.theme_file_edit)
        theme_row.addWidget(self.theme_load_button)
        theme_row.addWidget(self.theme_save_button)
        form_layout.addRow("Theme file:", theme_row)

        form_layout.addRow("Legend mode:", self.mode_selector)
        form_layout.addRow("", self.shift_enabled_checkbox)
        form_layout.addRow("", self.alternate_graphic_enabled_checkbox)
        form_layout.addRow("", self.function_enabled_checkbox)
        form_layout.addRow("Primary font size (millimeter):", self.primary_font_size_spin_box)
        form_layout.addRow("Shift font size (millimeter):", self.shift_font_size_spin_box)
        form_layout.addRow("AltGr font size (millimeter):", self.altcr_font_size_spin_box)
        form_layout.addRow("Fn font size (millimeter):", self.function_font_size_spin_box)
        form_layout.addRow("Depth or height (millimeter):", self.depth_spin_box)
        form_layout.addRow("Primary offset X (millimeter):", self.primary_offset_x_spin_box)
        form_layout.addRow("Primary offset Y (millimeter):", self.primary_offset_y_spin_box)
        form_layout.addRow("Shift offset X (millimeter):", self.shift_offset_x_spin_box)
        form_layout.addRow("Shift offset Y (millimeter):", self.shift_offset_y_spin_box)
        form_layout.addRow("AltGr offset X (millimeter):", self.altcr_offset_x_spin_box)
        form_layout.addRow("AltGr offset Y (millimeter):", self.altcr_offset_y_spin_box)
        form_layout.addRow("Fn offset X (millimeter):", self.function_offset_x_spin_box)
        form_layout.addRow("Fn offset Y (millimeter):", self.function_offset_y_spin_box)
        form_layout.addRow("Mesh linear deflection:", self.linear_deflection_spin_box)

        preview_row = QtWidgets.QHBoxLayout()
        preview_row.addWidget(QtWidgets.QLabel("Label:"))
        preview_row.addWidget(self.preview_label_edit)
        preview_row.addWidget(self.preview_update_button)
        preview_row.addWidget(self.preview_clear_button)
        form_layout.addRow("Preview:", preview_row)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.resize(820, 0)
        self.theme_extra_values: Dict[str, object] = {}

    def reload_fonts(self) -> None:
        include_variable = bool(self.include_variable_fonts_checkbox.isChecked())
        self.font_paths = scan_font_files(DEFAULT_FONT_DIRECTORIES, include_variable_fonts=include_variable)

        self.font_selector.clear()
        self.font_path_by_index.clear()
        for index, font_path in enumerate(self.font_paths):
            self.font_selector.addItem(font_display_name(font_path))
            self.font_path_by_index[index] = font_path

    def browse_font(self) -> None:
        start_directory = "/usr/share/fonts" if os.path.isdir("/usr/share/fonts") else os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select font", start_directory, "Fonts (*.ttf *.otf)"
        )
        if not path:
            return

        if (not self.include_variable_fonts_checkbox.isChecked()) and is_variable_font_filename(path):
            App.Console.PrintMessage(
                "Warning: variable font selected; Draft ShapeString may fail. "
                "If it fails, pick a non-variable TTF or OTF.\n"
            )

        if path not in self.font_paths:
            self.font_paths.append(path)
            self.font_paths = sorted(set(self.font_paths), key=lambda font_path: font_path.lower())
            self.font_selector.clear()
            self.font_path_by_index.clear()
            for index, font_path in enumerate(self.font_paths):
                self.font_selector.addItem(font_display_name(font_path))
                self.font_path_by_index[index] = font_path

        for index in range(self.font_selector.count()):
            if self.font_path_by_index.get(index) == path:
                self.font_selector.setCurrentIndex(index)
                break

    def browse_output_directory(self) -> None:
        start_directory = self.output_directory_edit.text().strip() or os.path.expanduser("~")
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder", start_directory)
        if path:
            self.output_directory_edit.setText(path)

    def browse_layout_file(self) -> None:
        start_directory = self.layout_file_edit.text().strip() or os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select layout file", start_directory, "CSV (*.csv)")
        if not path:
            return

        self.layout_file_edit.setText(path)

        with open(path, newline="", encoding="utf-8") as file_handle:
            reader = csv.DictReader(file_handle)
            primary_label = ""
            for row in reader:
                primary_label = (row.get("primary") or "").strip()
                if primary_label:
                    break

        if primary_label:
            self.preview_label_edit.setText(primary_label)

    def load_theme(self) -> None:
        start_directory = self.theme_file_edit.text().strip() or os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select theme file", start_directory, "Theme (*.theme *.json);;All files (*)"
        )
        if not path:
            return

        with open(path, encoding="utf-8") as file_handle:
            theme_data = json.load(file_handle)
        theme_values = theme_data.get("values", theme_data)
        if not isinstance(theme_values, dict):
            raise ValueError("Theme file has no values dictionary.")

        self.apply_theme_values(theme_values)
        self.theme_file_edit.setText(path)

    def save_theme(self) -> None:
        start_directory = self.theme_file_edit.text().strip() or os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save theme file", start_directory, "Theme (*.theme *.json);;All files (*)"
        )
        if not path:
            return

        theme_values = self.collect_theme_values()
        theme_data = {
            "format": "keycap-exporter-theme",
            "version": 1,
            "values": theme_values,
        }
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(theme_data, file_handle, indent=2, ensure_ascii=False)
        self.theme_file_edit.setText(path)

    def apply_theme_values(self, theme_values: Dict[str, object]) -> None:
        known_keys = {
            "template_object_name",
            "face_choice_label",
            "font_path",
            "output_directory",
            "layout_file_path",
            "mode",
            "primary_font_size_millimeter",
            "primary_offset_x_millimeter",
            "primary_offset_y_millimeter",
            "shift_font_size_millimeter",
            "shift_offset_x_millimeter",
            "shift_offset_y_millimeter",
            "altcr_font_size_millimeter",
            "altcr_offset_x_millimeter",
            "altcr_offset_y_millimeter",
            "function_font_size_millimeter",
            "function_offset_x_millimeter",
            "function_offset_y_millimeter",
            "depth_millimeter",
            "linear_deflection",
            "preview_label",
            "include_variable_fonts",
            "enable_shift_legend",
            "enable_alternate_graphic_legend",
            "enable_function_legend",
        }
        self.theme_extra_values = {key: value for key, value in theme_values.items() if key not in known_keys}

        include_variable_fonts = bool(theme_values.get("include_variable_fonts", False))
        self.include_variable_fonts_checkbox.setChecked(include_variable_fonts)
        self.reload_fonts()

        template_object_name = str(theme_values.get("template_object_name", "") or "")
        if template_object_name:
            for index, name in self.template_name_by_index.items():
                if name == template_object_name:
                    self.template_selector.setCurrentIndex(index)
                    break

        face_choice_label = str(theme_values.get("face_choice_label", "") or "")
        if face_choice_label:
            for index in range(self.face_selector.count()):
                if self.face_selector.itemText(index) == face_choice_label:
                    self.face_selector.setCurrentIndex(index)
                    break

        font_path = str(theme_values.get("font_path", "") or "")
        if font_path:
            if font_path not in self.font_paths:
                self.font_paths.append(font_path)
                self.font_paths = sorted(set(self.font_paths), key=lambda path: path.lower())
                self.font_selector.clear()
                self.font_path_by_index.clear()
                for index, path in enumerate(self.font_paths):
                    self.font_selector.addItem(font_display_name(path))
                    self.font_path_by_index[index] = path
            for index in range(self.font_selector.count()):
                if self.font_path_by_index.get(index) == font_path:
                    self.font_selector.setCurrentIndex(index)
                    break

        output_directory = str(theme_values.get("output_directory", "") or "")
        if output_directory:
            self.output_directory_edit.setText(output_directory)

        layout_file_path = str(theme_values.get("layout_file_path", "") or "")
        if layout_file_path:
            self.layout_file_edit.setText(layout_file_path)

        mode = str(theme_values.get("mode", "") or "")
        if mode:
            for index in range(self.mode_selector.count()):
                if self.mode_selector.itemText(index) == mode:
                    self.mode_selector.setCurrentIndex(index)
                    break

        self.primary_font_size_spin_box.setValue(float(theme_values.get("primary_font_size_millimeter", 6.0)))
        self.shift_font_size_spin_box.setValue(float(theme_values.get("shift_font_size_millimeter", 4.0)))
        self.altcr_font_size_spin_box.setValue(float(theme_values.get("altcr_font_size_millimeter", 4.0)))
        self.function_font_size_spin_box.setValue(float(theme_values.get("function_font_size_millimeter", 4.0)))
        self.depth_spin_box.setValue(float(theme_values.get("depth_millimeter", 0.6)))
        self.primary_offset_x_spin_box.setValue(float(theme_values.get("primary_offset_x_millimeter", -2.0)))
        self.primary_offset_y_spin_box.setValue(float(theme_values.get("primary_offset_y_millimeter", 0.0)))
        self.shift_offset_x_spin_box.setValue(float(theme_values.get("shift_offset_x_millimeter", 2.0)))
        self.shift_offset_y_spin_box.setValue(float(theme_values.get("shift_offset_y_millimeter", 2.0)))
        self.altcr_offset_x_spin_box.setValue(float(theme_values.get("altcr_offset_x_millimeter", 2.0)))
        self.altcr_offset_y_spin_box.setValue(float(theme_values.get("altcr_offset_y_millimeter", -2.0)))
        self.function_offset_x_spin_box.setValue(float(theme_values.get("function_offset_x_millimeter", 0.0)))
        self.function_offset_y_spin_box.setValue(float(theme_values.get("function_offset_y_millimeter", -2.0)))
        self.linear_deflection_spin_box.setValue(float(theme_values.get("linear_deflection", 0.08)))

        preview_label = str(theme_values.get("preview_label", "") or "")
        if preview_label:
            self.preview_label_edit.setText(preview_label)

        self.shift_enabled_checkbox.setChecked(bool(theme_values.get("enable_shift_legend", True)))
        self.alternate_graphic_enabled_checkbox.setChecked(
            bool(theme_values.get("enable_alternate_graphic_legend", True))
        )
        self.function_enabled_checkbox.setChecked(bool(theme_values.get("enable_function_legend", True)))

    def collect_theme_values(self) -> Dict[str, object]:
        template_index = int(self.template_selector.currentIndex())
        template_name = self.template_name_by_index.get(template_index, "")

        font_index = int(self.font_selector.currentIndex())
        font_path = self.font_path_by_index.get(font_index, "")

        values = dict(self.theme_extra_values)
        values.update(
            {
                "template_object_name": template_name,
                "face_choice_label": self.face_selector.currentText().strip(),
                "font_path": font_path,
                "output_directory": self.output_directory_edit.text().strip(),
                "layout_file_path": self.layout_file_edit.text().strip(),
                "mode": self.mode_selector.currentText().strip().lower(),
                "primary_font_size_millimeter": float(self.primary_font_size_spin_box.value()),
                "primary_offset_x_millimeter": float(self.primary_offset_x_spin_box.value()),
                "primary_offset_y_millimeter": float(self.primary_offset_y_spin_box.value()),
                "shift_font_size_millimeter": float(self.shift_font_size_spin_box.value()),
                "shift_offset_x_millimeter": float(self.shift_offset_x_spin_box.value()),
                "shift_offset_y_millimeter": float(self.shift_offset_y_spin_box.value()),
                "altcr_font_size_millimeter": float(self.altcr_font_size_spin_box.value()),
                "altcr_offset_x_millimeter": float(self.altcr_offset_x_spin_box.value()),
                "altcr_offset_y_millimeter": float(self.altcr_offset_y_spin_box.value()),
                "function_font_size_millimeter": float(self.function_font_size_spin_box.value()),
                "function_offset_x_millimeter": float(self.function_offset_x_spin_box.value()),
                "function_offset_y_millimeter": float(self.function_offset_y_spin_box.value()),
                "depth_millimeter": float(self.depth_spin_box.value()),
                "linear_deflection": float(self.linear_deflection_spin_box.value()),
                "preview_label": self.preview_label_edit.text().strip(),
                "include_variable_fonts": bool(self.include_variable_fonts_checkbox.isChecked()),
                "enable_shift_legend": bool(self.shift_enabled_checkbox.isChecked()),
                "enable_alternate_graphic_legend": bool(self.alternate_graphic_enabled_checkbox.isChecked()),
                "enable_function_legend": bool(self.function_enabled_checkbox.isChecked()),
            }
        )
        return values

    def get_configuration_for_preview(self) -> ExportConfiguration:
        if len(self.solid_objects) == 0:
            raise RuntimeError("No solid template object available. Use a Body or feature that produces a solid.")

        for spin_box in (
            self.primary_font_size_spin_box,
            self.shift_font_size_spin_box,
            self.altcr_font_size_spin_box,
            self.function_font_size_spin_box,
            self.depth_spin_box,
            self.primary_offset_x_spin_box,
            self.primary_offset_y_spin_box,
            self.shift_offset_x_spin_box,
            self.shift_offset_y_spin_box,
            self.altcr_offset_x_spin_box,
            self.altcr_offset_y_spin_box,
            self.function_offset_x_spin_box,
            self.function_offset_y_spin_box,
            self.linear_deflection_spin_box,
        ):
            spin_box.interpretText()

        template_index = int(self.template_selector.currentIndex())
        template_name = self.template_name_by_index.get(template_index, "")

        font_index = int(self.font_selector.currentIndex())
        font_path = self.font_path_by_index.get(font_index, "")

        return ExportConfiguration(
            template_object_name=template_name,
            face_choice_label=self.face_selector.currentText().strip(),
            font_path=font_path,
            output_directory=self.output_directory_edit.text().strip(),
            layout_file_path=self.layout_file_edit.text().strip(),
            mode=self.mode_selector.currentText().strip().lower(),
            enable_shift_legend=bool(self.shift_enabled_checkbox.isChecked()),
            enable_alternate_graphic_legend=bool(self.alternate_graphic_enabled_checkbox.isChecked()),
            enable_function_legend=bool(self.function_enabled_checkbox.isChecked()),
            primary_font_size_millimeter=float(self.primary_font_size_spin_box.value()),
            primary_offset_x_millimeter=float(self.primary_offset_x_spin_box.value()),
            primary_offset_y_millimeter=float(self.primary_offset_y_spin_box.value()),
            shift_font_size_millimeter=float(self.shift_font_size_spin_box.value()),
            shift_offset_x_millimeter=float(self.shift_offset_x_spin_box.value()),
            shift_offset_y_millimeter=float(self.shift_offset_y_spin_box.value()),
            altcr_font_size_millimeter=float(self.altcr_font_size_spin_box.value()),
            altcr_offset_x_millimeter=float(self.altcr_offset_x_spin_box.value()),
            altcr_offset_y_millimeter=float(self.altcr_offset_y_spin_box.value()),
            function_font_size_millimeter=float(self.function_font_size_spin_box.value()),
            function_offset_x_millimeter=float(self.function_offset_x_spin_box.value()),
            function_offset_y_millimeter=float(self.function_offset_y_spin_box.value()),
            depth_millimeter=float(self.depth_spin_box.value()),
            linear_deflection=float(self.linear_deflection_spin_box.value()),
            preview_label=self.preview_label_edit.text().strip() or "A",
        )

   

    def update_preview_clicked(self) -> None:
        generate_configuration = self.get_configuration_for_preview()

        template_object = resolve_object_by_name(App.ActiveDocument, generate_configuration.template_object_name)
        blank_key = template_object.Shape.copy()

        preview_label = generate_configuration.preview_label
        shift_label = None
        altcr_label = None
        function_label = None
        layout_file_path = generate_configuration.layout_file_path
        if layout_file_path and os.path.isfile(layout_file_path):
            entries = read_layout_entries(layout_file_path)
            if entries:
                preview_label, shift_label, altcr_label, function_label, _ = entries[0]
        if not generate_configuration.enable_shift_legend:
            shift_label = None
        if not generate_configuration.enable_alternate_graphic_legend:
            altcr_label = None
        if not generate_configuration.enable_function_legend:
            function_label = None

        preview_shape = build_keycap_shape_from_configuration(
            self.document,
            blank_key,
            generate_configuration,
            preview_label,
            shift_label,
            altcr_label,
            function_label,
        )

        set_preview_shape(self.document, preview_shape)
        Gui.ActiveDocument.ActiveView.fitAll()

    def clear_preview_clicked(self) -> None:
        remove_existing_preview(self.document)

    def get_configuration(self) -> ExportConfiguration:
        return self.get_configuration_for_preview()
