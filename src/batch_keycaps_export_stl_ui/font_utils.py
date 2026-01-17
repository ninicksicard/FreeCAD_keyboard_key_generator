"""Font scanning helpers."""

import os


def is_variable_font_filename(font_path):
    base = os.path.basename(font_path).lower()
    return "variablefont" in base or "variable-font" in base


def scan_ttf_otf_files(font_dirs, include_variable_fonts):
    font_paths = []
    for root_dir in font_dirs:
        if not os.path.isdir(root_dir):
            continue
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                lower_name = filename.lower()
                if not (lower_name.endswith(".ttf") or lower_name.endswith(".otf")):
                    continue
                full_path = os.path.join(dirpath, filename)
                if (not include_variable_fonts) and is_variable_font_filename(full_path):
                    continue
                font_paths.append(full_path)

    return sorted(set(font_paths), key=lambda path: path.lower())


def font_display_name(font_path):
    return os.path.basename(font_path)
