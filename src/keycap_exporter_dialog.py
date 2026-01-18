"""
File: keycap_exporter_dialog.py

Batch keycap STL export dialog for FreeCAD.

Theme files are stored using jsonpickle to minimize boilerplate:
we encode/decode a single configuration wrapper instance at once.
"""

import csv
import os
from dataclasses import dataclass
from typing import Dict, List

import FreeCAD as App
import FreeCADGui as Gui
import jsonpickle
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


@dataclass
class ThemeConfiguration:
    """
    File: keycap_exporter_dialog.py

    Theme wrapper persisted via jsonpickle.

    This is intentionally a single object so theme save/load is just:
    - encode one instance
    - decode one instance
    """
    export_configuration: ExportConfiguration
    include_variable_fonts: bool = False


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
            raw_text = file_handle.read()

        decoded_object = None
        decode_error: Exception | None = None
        try:
            decoded_object = jsonpickle.decode(raw_text)
        except Exception as exception:
            decode_error = exception

        if isinstance(decoded_object, ThemeConfiguration):
            self.apply_theme_configuration(decoded_object)
            self.theme_file_edit.setText(path)
        


    def save_theme(self) -> None:
        start_directory = self.theme_file_edit.text().strip() or os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save theme file", start_directory, "Theme (*.theme *.json);;All files (*)"
        )
        if not path:
            return

        theme_configuration = self.collect_theme_configuration()

        serialized = jsonpickle.encode(
            theme_configuration,
            unpicklable=True,
            indent=2,
            make_refs=False,
        )
        with open(path, "w", encoding="utf-8") as file_handle:
            file_handle.write(serialized)

        self.theme_file_edit.setText(path)

    def apply_theme_configuration(self, theme_configuration: ThemeConfiguration) -> None:
        self.include_variable_fonts_checkbox.setChecked(bool(theme_configuration.include_variable_fonts))
        self.reload_fonts()

        export_configuration = theme_configuration.export_configuration

        template_object_name = str(getattr(export_configuration, "template_object_name", "") or "")
        if template_object_name:
            for index, name in self.template_name_by_index.items():
                if name == template_object_name:
                    self.template_selector.setCurrentIndex(index)
                    break

        face_choice_label = str(getattr(export_configuration, "face_choice_label", "") or "")
        if face_choice_label:
            for index in range(self.face_selector.count()):
                if self.face_selector.itemText(index) == face_choice_label:
                    self.face_selector.setCurrentIndex(index)
                    break

        font_path = str(getattr(export_configuration, "font_path", "") or "")
        if font_path:
            if font_path not in self.font_paths:
                self.font_paths.append(font_path)
                self.font_paths = sorted(set(self.font_paths), key=lambda path: path.lower())
                self.font_selector.clear()
                self.font_path_by_index.clear()
                for index, font_path_item in enumerate(self.font_paths):
                    self.font_selector.addItem(font_display_name(font_path_item))
                    self.font_path_by_index[index] = font_path_item
            for index in range(self.font_selector.count()):
                if self.font_path_by_index.get(index) == font_path:
                    self.font_selector.setCurrentIndex(index)
                    break

        output_directory = str(getattr(export_configuration, "output_directory", "") or "")
        if output_directory:
            self.output_directory_edit.setText(output_directory)

        layout_file_path = str(getattr(export_configuration, "layout_file_path", "") or "")
        if layout_file_path:
            self.layout_file_edit.setText(layout_file_path)

        mode = str(getattr(export_configuration, "mode", "") or "")
        if mode:
            for index in range(self.mode_selector.count()):
                if self.mode_selector.itemText(index) == mode:
                    self.mode_selector.setCurrentIndex(index)
                    break

        self.primary_font_size_spin_box.setValue(float(getattr(export_configuration, "primary_font_size_millimeter", 6.0)))
        self.shift_font_size_spin_box.setValue(float(getattr(export_configuration, "shift_font_size_millimeter", 4.0)))
        self.altcr_font_size_spin_box.setValue(float(getattr(export_configuration, "altcr_font_size_millimeter", 4.0)))
        self.function_font_size_spin_box.setValue(float(getattr(export_configuration, "function_font_size_millimeter", 4.0)))
        self.depth_spin_box.setValue(float(getattr(export_configuration, "depth_millimeter", 0.6)))
        self.primary_offset_x_spin_box.setValue(float(getattr(export_configuration, "primary_offset_x_millimeter", -2.0)))
        self.primary_offset_y_spin_box.setValue(float(getattr(export_configuration, "primary_offset_y_millimeter", 0.0)))
        self.shift_offset_x_spin_box.setValue(float(getattr(export_configuration, "shift_offset_x_millimeter", 2.0)))
        self.shift_offset_y_spin_box.setValue(float(getattr(export_configuration, "shift_offset_y_millimeter", 2.0)))
        self.altcr_offset_x_spin_box.setValue(float(getattr(export_configuration, "altcr_offset_x_millimeter", 2.0)))
        self.altcr_offset_y_spin_box.setValue(float(getattr(export_configuration, "altcr_offset_y_millimeter", -2.0)))
        self.function_offset_x_spin_box.setValue(float(getattr(export_configuration, "function_offset_x_millimeter", 0.0)))
        self.function_offset_y_spin_box.setValue(float(getattr(export_configuration, "function_offset_y_millimeter", -2.0)))
        self.linear_deflection_spin_box.setValue(float(getattr(export_configuration, "linear_deflection", 0.08)))

        preview_label = str(getattr(export_configuration, "preview_label", "") or "")
        if preview_label:
            self.preview_label_edit.setText(preview_label)

        self.shift_enabled_checkbox.setChecked(bool(getattr(export_configuration, "enable_shift_legend", True)))
        self.alternate_graphic_enabled_checkbox.setChecked(
            bool(getattr(export_configuration, "enable_alternate_graphic_legend", True))
        )
        self.function_enabled_checkbox.setChecked(bool(getattr(export_configuration, "enable_function_legend", True)))

    def collect_theme_configuration(self) -> ThemeConfiguration:
        export_configuration = self.get_configuration_for_preview()
        include_variable_fonts = bool(self.include_variable_fonts_checkbox.isChecked())
        return ThemeConfiguration(
            export_configuration=export_configuration,
            include_variable_fonts=include_variable_fonts,
        )


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
