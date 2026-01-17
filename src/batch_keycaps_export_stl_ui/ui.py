"""Qt dialog UI for batch export."""

import os
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets

from batch_keycaps_export_stl_ui import config
from batch_keycaps_export_stl_ui import core
from batch_keycaps_export_stl_ui import font_utils
from batch_keycaps_export_stl_ui import object_utils
from batch_keycaps_export_stl_ui import preview_utils


def _main_constants():
    main_mod = sys.modules["main"]
    return main_mod.DEFAULT_FONT_DIRS, main_mod.FACE_DIRECTIONS


class BatchKeycapDialog(QtWidgets.QDialog):
    def __init__(self, doc):
        super().__init__(Gui.getMainWindow())
        self.setWindowTitle("Batch Keycap STL Export")

        self._doc = doc

        self._solid_objects = object_utils.list_solid_objects(doc)

        self.template_combo = QtWidgets.QComboBox()
        self._template_name_by_index = {}
        for index, obj in enumerate(self._solid_objects):
            self.template_combo.addItem(object_utils.object_display_name(obj))
            self._template_name_by_index[index] = obj.Name

        self.face_combo = QtWidgets.QComboBox()
        _default_font_dirs, face_directions = _main_constants()
        for face_label in face_directions.keys():
            self.face_combo.addItem(face_label)

        self.include_variable_fonts_checkbox = QtWidgets.QCheckBox("Include variable fonts")
        self.include_variable_fonts_checkbox.setChecked(False)
        self.include_variable_fonts_checkbox.stateChanged.connect(self._reload_fonts)

        self.font_combo = QtWidgets.QComboBox()
        self._font_paths = []
        self._font_path_by_index = {}

        self.font_browse_btn = QtWidgets.QPushButton("Browse...")
        self.font_browse_btn.clicked.connect(self._browse_font)

        self.output_dir_edit = QtWidgets.QLineEdit(os.path.expanduser("~/keycaps_stl_out"))
        self.output_browse_btn = QtWidgets.QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self._browse_output_dir)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["engrave", "raise"])

        self.size_spin = QtWidgets.QDoubleSpinBox()
        self.size_spin.setRange(1.0, 50.0)
        self.size_spin.setDecimals(2)
        self.size_spin.setValue(6.0)

        self.depth_spin = QtWidgets.QDoubleSpinBox()
        self.depth_spin.setRange(0.05, 10.0)
        self.depth_spin.setDecimals(2)
        self.depth_spin.setValue(0.6)

        self.offset_x_spin = QtWidgets.QDoubleSpinBox()
        self.offset_x_spin.setRange(-50.0, 50.0)
        self.offset_x_spin.setDecimals(2)
        self.offset_x_spin.setValue(0.0)

        self.offset_y_spin = QtWidgets.QDoubleSpinBox()
        self.offset_y_spin.setRange(-50.0, 50.0)
        self.offset_y_spin.setDecimals(2)
        self.offset_y_spin.setValue(0.0)

        self.linear_defl_spin = QtWidgets.QDoubleSpinBox()
        self.linear_defl_spin.setRange(0.01, 2.0)
        self.linear_defl_spin.setDecimals(3)
        self.linear_defl_spin.setValue(0.08)

        self.preview_label_edit = QtWidgets.QLineEdit("A")
        self.preview_update_btn = QtWidgets.QPushButton("Update Preview")
        self.preview_clear_btn = QtWidgets.QPushButton("Clear Preview")

        self.preview_update_btn.clicked.connect(self._update_preview_clicked)
        self.preview_clear_btn.clicked.connect(self._clear_preview_clicked)

        self._reload_fonts()

        form = QtWidgets.QFormLayout()

        if len(self._solid_objects) == 0:
            warning = QtWidgets.QLabel(
                "No solid template objects found in this document (need Shape with Solids)."
            )
            warning.setStyleSheet("color: #cc0000;")
            form.addRow("Template:", warning)
        else:
            form.addRow("Template object:", self.template_combo)

        form.addRow("Legend face:", self.face_combo)

        font_row = QtWidgets.QHBoxLayout()
        font_row.addWidget(self.font_combo)
        font_row.addWidget(self.font_browse_btn)
        form.addRow("Font:", font_row)
        form.addRow("", self.include_variable_fonts_checkbox)

        out_row = QtWidgets.QHBoxLayout()
        out_row.addWidget(self.output_dir_edit)
        out_row.addWidget(self.output_browse_btn)
        form.addRow("Output folder:", out_row)

        form.addRow("Legend mode:", self.mode_combo)
        form.addRow("Font size (mm):", self.size_spin)
        form.addRow("Depth/height (mm):", self.depth_spin)
        form.addRow("Legend offset X (mm):", self.offset_x_spin)
        form.addRow("Legend offset Y (mm):", self.offset_y_spin)
        form.addRow("Mesh linear deflection:", self.linear_defl_spin)

        preview_row = QtWidgets.QHBoxLayout()
        preview_row.addWidget(QtWidgets.QLabel("Label:"))
        preview_row.addWidget(self.preview_label_edit)
        preview_row.addWidget(self.preview_update_btn)
        preview_row.addWidget(self.preview_clear_btn)
        form.addRow("Preview:", preview_row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.resize(820, 0)

    def _reload_fonts(self):
        include_variable = bool(self.include_variable_fonts_checkbox.isChecked())
        default_font_dirs, _face_directions = _main_constants()
        self._font_paths = font_utils.scan_ttf_otf_files(
            default_font_dirs, include_variable_fonts=include_variable
        )

        self.font_combo.clear()
        self._font_path_by_index.clear()
        for index, font_path in enumerate(self._font_paths):
            self.font_combo.addItem(font_utils.font_display_name(font_path))
            self._font_path_by_index[index] = font_path

    def _browse_font(self):
        start_dir = "/usr/share/fonts" if os.path.isdir("/usr/share/fonts") else os.path.expanduser("~")
        path, _unused = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select font", start_dir, "Fonts (*.ttf *.otf)"
        )
        if not path:
            return

        if (not self.include_variable_fonts_checkbox.isChecked()) and font_utils.is_variable_font_filename(
            path
        ):
            App.Console.PrintMessage(
                "Warning: variable font selected; Draft ShapeString may fail. "
                "If it fails, pick a non-variable TTF/OTF.\n"
            )

        if path not in self._font_paths:
            self._font_paths.append(path)
            self._font_paths = sorted(set(self._font_paths), key=lambda p: p.lower())
            self.font_combo.clear()
            self._font_path_by_index.clear()
            for index, font_path in enumerate(self._font_paths):
                self.font_combo.addItem(font_utils.font_display_name(font_path))
                self._font_path_by_index[index] = font_path

        for index in range(self.font_combo.count()):
            if self._font_path_by_index.get(index) == path:
                self.font_combo.setCurrentIndex(index)
                break

    def _browse_output_dir(self):
        start_dir = self.output_dir_edit.text().strip() or os.path.expanduser("~")
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder", start_dir)
        if path:
            self.output_dir_edit.setText(path)

    def _get_config_for_preview(self):
        if len(self._solid_objects) == 0:
            raise RuntimeError("No solid template object available. Use a Body/feature that produces a solid.")

        template_index = int(self.template_combo.currentIndex())
        template_name = self._template_name_by_index.get(template_index, "")

        font_index = int(self.font_combo.currentIndex())
        font_path = self._font_path_by_index.get(font_index, "")

        return config.ExportConfig(
            template_object_name=template_name,
            face_choice_label=self.face_combo.currentText().strip(),
            font_path=font_path,
            output_dir=self.output_dir_edit.text().strip(),
            mode=self.mode_combo.currentText().strip().lower(),
            size_mm=float(self.size_spin.value()),
            depth_mm=float(self.depth_spin.value()),
            offset_x_mm=float(self.offset_x_spin.value()),
            offset_y_mm=float(self.offset_y_spin.value()),
            linear_deflection=float(self.linear_defl_spin.value()),
            preview_label=self.preview_label_edit.text().strip() or "A",
        )

    def _update_preview_clicked(self):
        cfg = self._get_config_for_preview()
        _default_font_dirs, face_directions = _main_constants()
        try:
            preview_shape = core.build_keycap_with_legend_shape(
                doc=self._doc,
                cfg=cfg,
                label=cfg.preview_label,
                face_directions=face_directions,
            )
            preview_utils.set_preview_shape(self._doc, preview_shape)
            Gui.ActiveDocument.ActiveView.fitAll()
        except Exception as exc:
            App.Console.PrintError("Preview failed: %s\n" % exc)

    def _clear_preview_clicked(self):
        preview_utils.remove_existing_preview(self._doc)

    def get_config(self):
        return self._get_config_for_preview()
