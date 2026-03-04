"""
P-RHO Matrix Processor - PyQt5 GUI
"""

import sys
import re
import numpy as np
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QSlider, QCheckBox, QLineEdit, QGroupBox, QMessageBox, QFrame,
    QTabWidget, QProgressBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class PRhoProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("P-RHO Matrix Processor")
        self.setMinimumSize(800, 600)

        # Data
        self.p_file = None
        self.rho_file = None
        self.output_dir = None
        self.final_table = None
        self.rho_matrix = None  # Full RHO matrix for edge file
        self.p_matrix = None    # Full P matrix for masking

        self.region_names = [
            "L.CAC", "R.CAC", "L.CMF", "R.CMF", "L.IP", "R.IP", "L.INS", "R.INS",
            "L.IST", "R.IST", "L.MOF", "R.MOF", "L.MT", "R.MT", "L.PHIP", "R.PHIP",
            "L.PCG", "R.PCG", "L.PREC", "R.PREC", "L.RAC", "R.RAC", "L.RMF", "R.RMF",
            "L.SF", "R.SF", "L.SP", "R.SP"
        ]

        self.batch_folder = None
        self.batch_pairs = []

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        single_tab = QWidget()
        self.tabs.addTab(single_tab, "Single File")
        self._setup_single_tab(single_tab)

        batch_tab = QWidget()
        self.tabs.addTab(batch_tab, "Batch Processing")
        self._setup_batch_tab(batch_tab)

    def _setup_single_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # === File Selection ===
        file_group = QGroupBox("1. Select Files")
        file_layout = QVBoxLayout(file_group)

        # P-file row
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("P-values:"))
        self.p_label = QLabel("No file selected")
        self.p_label.setStyleSheet("color: gray;")
        p_row.addWidget(self.p_label, 1)
        p_btn = QPushButton("Browse P-file")
        p_btn.clicked.connect(self.select_p_file)
        p_row.addWidget(p_btn)
        file_layout.addLayout(p_row)

        # RHO-file row
        rho_row = QHBoxLayout()
        rho_row.addWidget(QLabel("RHO-values:"))
        self.rho_label = QLabel("No file selected")
        self.rho_label.setStyleSheet("color: gray;")
        rho_row.addWidget(self.rho_label, 1)
        rho_btn = QPushButton("Browse RHO-file")
        rho_btn.clicked.connect(self.select_rho_file)
        rho_row.addWidget(rho_btn)
        file_layout.addLayout(rho_row)

        layout.addWidget(file_group)

        # === Settings ===
        settings_group = QGroupBox("2. Settings")
        settings_layout = QVBoxLayout(settings_group)

        # P-threshold slider
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("P-value threshold:"))
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(1, 300)  # 0.001 to 0.300
        self.thresh_slider.setValue(50)  # 0.05
        self.thresh_slider.valueChanged.connect(self.update_thresh_label)
        thresh_row.addWidget(self.thresh_slider)
        self.thresh_label = QLabel("0.050")
        self.thresh_label.setMinimumWidth(50)
        thresh_row.addWidget(self.thresh_label)
        settings_layout.addLayout(thresh_row)

        # Invert RHO checkbox
        self.invert_check = QCheckBox("Invert RHO values (multiply by -1)")
        self.invert_check.setChecked(True)
        settings_layout.addWidget(self.invert_check)

        layout.addWidget(settings_group)

        # === Process Button ===
        self.process_btn = QPushButton("Process Files")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.process_btn.clicked.connect(self.process_files)
        layout.addWidget(self.process_btn)

        # === Results Table ===
        results_group = QGroupBox("3. Results")
        results_layout = QVBoxLayout(results_group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Region 1", "Region 2", "P-Value", "RHO-Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.table)

        self.result_status = QLabel("")
        results_layout.addWidget(self.result_status)

        layout.addWidget(results_group)

        # === Export ===
        export_group = QGroupBox("4. Export")
        export_layout = QVBoxLayout(export_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Output name:"))
        self.output_name = QLineEdit("output")
        name_row.addWidget(self.output_name)
        export_layout.addLayout(name_row)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export .edge + .xlsx")
        export_btn.setMinimumHeight(35)
        export_btn.clicked.connect(self.export_files)
        btn_row.addWidget(export_btn)
        export_layout.addLayout(btn_row)

        self.export_status = QLabel("")
        export_layout.addWidget(self.export_status)

        layout.addWidget(export_group)

    def update_thresh_label(self, value):
        self.thresh_label.setText(f"{value / 1000:.3f}")

    def select_p_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select P-values file", "", "Text files (*.txt);;All files (*)"
        )
        if file:
            self.p_file = file
            self.output_dir = str(Path(file).parent)
            self.p_label.setText(Path(file).name)
            self.p_label.setStyleSheet("color: green;")
            self._auto_find_rho(file)
            self._set_output_name(file)

    def select_rho_file(self):
        start_dir = self.output_dir or ""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select RHO-values file", start_dir, "Text files (*.txt);;All files (*)"
        )
        if file:
            self.rho_file = file
            self.rho_label.setText(Path(file).name)
            self.rho_label.setStyleSheet("color: green;")

    def _auto_find_rho(self, p_file):
        """Auto-detect RHO file based on P file name."""
        p_path = Path(p_file)
        patterns = [("-p-", "-RHO-"), ("-p-", "-rho-"), ("_p_", "_RHO_"), ("_p_", "_rho_")]

        for p_pat, rho_pat in patterns:
            if p_pat in p_path.name:
                rho_name = p_path.name.replace(p_pat, rho_pat)
                rho_path = p_path.parent / rho_name
                if rho_path.exists():
                    self.rho_file = str(rho_path)
                    self.rho_label.setText(rho_path.name)
                    self.rho_label.setStyleSheet("color: green;")
                    return

    def _set_output_name(self, p_file):
        """Generate output name from P file."""
        name = Path(p_file).stem
        for pattern in ["-p-", "_p_", "-p", "_p"]:
            name = name.replace(pattern, "")
        name = name.replace("Between", "").strip("-_")
        self.output_name.setText(name if name else "output")

    def process_files(self):
        if not self.p_file or not self.rho_file:
            QMessageBox.warning(self, "Error", "Please select both P and RHO files.")
            return

        try:
            threshold = self.thresh_slider.value() / 1000.0

            # Load data
            p_df = pd.read_csv(self.p_file, sep="\t", header=1)
            rho_df = pd.read_csv(self.rho_file, sep="\t", header=1)

            # Convert to numeric
            p_df = p_df.apply(pd.to_numeric, errors='coerce')
            rho_df = rho_df.apply(pd.to_numeric, errors='coerce')

            # Store full matrices
            self.p_matrix = p_df.copy()
            self.rho_matrix = rho_df.copy()

            # Apply RHO inversion FIRST if checked
            if self.invert_check.isChecked():
                self.rho_matrix = self.rho_matrix * (-1)

            # Lower triangular mask
            tril_mask = np.tril(np.ones(p_df.shape), k=0).astype(bool)

            p_filtered = pd.DataFrame(
                np.where(tril_mask, p_df.values, np.nan),
                index=p_df.index, columns=p_df.columns
            )
            rho_filtered = pd.DataFrame(
                np.where(tril_mask, self.rho_matrix.values, np.nan),
                index=rho_df.index, columns=rho_df.columns
            )

            # Apply threshold
            p_filtered = p_filtered.where((p_filtered < threshold) & (p_filtered > 0))

            # Combined mask
            mask = p_filtered.notna() & rho_filtered.notna()
            p_filtered = p_filtered.where(mask)
            rho_filtered = rho_filtered.where(mask)

            # Store for edge export - set non-significant to 0
            self.p_mask = p_filtered.notna()

            # Create long format table
            rows = []
            for i in range(len(p_filtered)):
                for j in range(len(p_filtered.columns)):
                    p_val = p_filtered.iloc[i, j]
                    rho_val = rho_filtered.iloc[i, j]
                    if pd.notna(p_val) and pd.notna(rho_val):
                        # Get region names
                        r1 = p_filtered.index[i]
                        r2 = p_filtered.columns[j]

                        # Map numeric to region names
                        if isinstance(r1, (int, float)) and not pd.isna(r1):
                            r1 = self.region_names[int(r1)] if int(r1) < len(self.region_names) else str(r1)
                        if isinstance(r2, (int, float)) and not pd.isna(r2):
                            r2 = self.region_names[int(r2)] if int(r2) < len(self.region_names) else str(r2)

                        # Skip unnamed columns
                        if str(r2).startswith('Unnamed'):
                            continue

                        rows.append({
                            'Region1': str(r1),
                            'Region2': str(r2),
                            'P_Values': p_val,
                            'RHO_Values': rho_val
                        })

            self.final_table = pd.DataFrame(rows)

            # Update table widget
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(row['Region1']))
                self.table.setItem(i, 1, QTableWidgetItem(row['Region2']))
                self.table.setItem(i, 2, QTableWidgetItem(f"{row['P_Values']:.4f}"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{row['RHO_Values']:.6f}"))

            self.table.resizeColumnsToContents()
            self.result_status.setText(f"Found {len(rows)} significant pairs (p < {threshold:.3f})")
            self.result_status.setStyleSheet("color: green;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Processing failed:\n{str(e)}")
            self.result_status.setText("Processing failed")
            self.result_status.setStyleSheet("color: red;")

    def export_files(self):
        if self.final_table is None or self.rho_matrix is None:
            QMessageBox.warning(self, "Error", "Please process files first.")
            return

        name = self.output_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter an output name.")
            return

        try:
            out_dir = Path(self.output_dir)
            edge_path = out_dir / f"{name}.edge"
            xlsx_path = out_dir / f"{name}.xlsx"

            # Export edge file
            # Drop first column if unnamed/index
            rho_export = self.rho_matrix.copy()
            first_col = rho_export.columns[0]
            if first_col == 0 or str(first_col).startswith('Unnamed'):
                rho_export = rho_export.iloc[:, 1:]

            # Apply mask - set non-significant values to 0
            threshold = self.thresh_slider.value() / 1000.0
            p_vals = self.p_matrix.copy()
            if p_vals.columns[0] == 0 or str(p_vals.columns[0]).startswith('Unnamed'):
                p_vals = p_vals.iloc[:, 1:]

            # Create significance mask (p < threshold)
            sig_mask = (p_vals < threshold) & (p_vals > 0)

            # Set non-significant RHO values to 0
            rho_export = rho_export.where(sig_mask, 0)

            # Write edge file
            d = rho_export.values
            d = np.nan_to_num(d, nan=0.0)

            with open(edge_path, 'w') as f:
                for row in d:
                    line = ' '.join(f"{val:.3f}" for val in row)
                    f.write(line + '\n')

            # Export Excel
            self.final_table.to_excel(xlsx_path, index=False)

            self.export_status.setText(f"Saved: {name}.edge and {name}.xlsx")
            self.export_status.setStyleSheet("color: green;")
            QMessageBox.information(self, "Success", f"Files saved to:\n{out_dir}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
            self.export_status.setStyleSheet("color: red;")

    # ===== Batch Processing =====

    def _setup_batch_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # === Folder Selection ===
        folder_group = QGroupBox("1. Select Folder")
        folder_layout = QVBoxLayout(folder_group)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        self.batch_folder_label = QLabel("No folder selected")
        self.batch_folder_label.setStyleSheet("color: gray;")
        folder_row.addWidget(self.batch_folder_label, 1)
        browse_btn = QPushButton("Browse Folder")
        browse_btn.clicked.connect(self._select_batch_folder)
        folder_row.addWidget(browse_btn)
        folder_layout.addLayout(folder_row)
        layout.addWidget(folder_group)

        # === Settings ===
        settings_group = QGroupBox("2. Settings")
        settings_layout = QVBoxLayout(settings_group)

        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("P-value threshold:"))
        self.batch_thresh_slider = QSlider(Qt.Horizontal)
        self.batch_thresh_slider.setRange(1, 300)
        self.batch_thresh_slider.setValue(50)
        self.batch_thresh_slider.valueChanged.connect(self._update_batch_thresh_label)
        thresh_row.addWidget(self.batch_thresh_slider)
        self.batch_thresh_label = QLabel("0.050")
        self.batch_thresh_label.setMinimumWidth(50)
        thresh_row.addWidget(self.batch_thresh_label)
        settings_layout.addLayout(thresh_row)

        self.batch_invert_check = QCheckBox("Invert RHO values (multiply by -1)")
        self.batch_invert_check.setChecked(True)
        settings_layout.addWidget(self.batch_invert_check)

        layout.addWidget(settings_group)

        # === Found Files ===
        found_group = QGroupBox("3. Found File Pairs")
        found_layout = QVBoxLayout(found_group)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(3)
        self.batch_table.setHorizontalHeaderLabels(["P-File", "RHO-File", "Output Name"])
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        found_layout.addWidget(self.batch_table)

        self.batch_found_label = QLabel("")
        found_layout.addWidget(self.batch_found_label)

        layout.addWidget(found_group)

        # === Run ===
        self.batch_run_btn = QPushButton("Run Batch Processing")
        self.batch_run_btn.setMinimumHeight(40)
        self.batch_run_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.batch_run_btn.clicked.connect(self._run_batch)
        self.batch_run_btn.setEnabled(False)
        layout.addWidget(self.batch_run_btn)

        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        layout.addWidget(self.batch_progress)

        self.batch_status = QLabel("")
        layout.addWidget(self.batch_status)

    def _update_batch_thresh_label(self, value):
        self.batch_thresh_label.setText(f"{value / 1000:.3f}")

    def _select_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Batch Processing")
        if folder:
            self.batch_folder = folder
            self.batch_folder_label.setText(folder)
            self.batch_folder_label.setStyleSheet("color: green;")
            self._scan_for_pairs()

    def _scan_for_pairs(self):
        """Recursively find P-RHO file pairs in the selected folder."""
        folder = Path(self.batch_folder)
        self.batch_pairs = []

        p_files = []
        for f in folder.rglob("*"):
            if f.is_file() and "-p-" in f.name.lower():
                p_files.append(f)

        for p_path in sorted(p_files):
            rho_path = None
            patterns = [("-p-", "-RHO-"), ("-p-", "-rho-"), ("_p_", "_RHO_"), ("_p_", "_rho_")]
            for p_pat, rho_pat in patterns:
                if p_pat in p_path.name:
                    rho_name = p_path.name.replace(p_pat, rho_pat)
                    candidate = p_path.parent / rho_name
                    if candidate.exists():
                        rho_path = candidate
                        break

            if rho_path:
                output_name = self._batch_output_name(p_path.name)
                self.batch_pairs.append((str(p_path), str(rho_path), output_name))

        self.batch_table.setRowCount(len(self.batch_pairs))
        for i, (p, r, name) in enumerate(self.batch_pairs):
            self.batch_table.setItem(i, 0, QTableWidgetItem(Path(p).name))
            self.batch_table.setItem(i, 1, QTableWidgetItem(Path(r).name))
            self.batch_table.setItem(i, 2, QTableWidgetItem(name))
        self.batch_table.resizeColumnsToContents()

        count = len(self.batch_pairs)
        self.batch_found_label.setText(f"Found {count} file pair(s)")
        self.batch_found_label.setStyleSheet("color: green;" if count > 0 else "color: red;")
        self.batch_run_btn.setEnabled(count > 0)

    def _batch_output_name(self, filename):
        """Generate output name from filename: remove -p-/-RHO- and trailing numerics."""
        name = Path(filename).stem
        name = re.split(r'-[pP]-|-[rR][hH][oO]-', name)[0]
        name = re.sub(r'_\d+\.?\d*$', '', name)
        name = name.strip('-_')
        return name if name else "output"

    def _run_batch(self):
        if not self.batch_pairs:
            return

        threshold = self.batch_thresh_slider.value() / 1000.0
        invert = self.batch_invert_check.isChecked()

        self.batch_progress.setVisible(True)
        self.batch_progress.setMaximum(len(self.batch_pairs))
        self.batch_progress.setValue(0)
        self.batch_run_btn.setEnabled(False)

        success = 0
        errors = []

        for idx, (p_file, rho_file, output_name) in enumerate(self.batch_pairs):
            try:
                self._process_and_export_pair(p_file, rho_file, output_name, threshold, invert)
                success += 1
            except Exception as e:
                errors.append(f"{Path(p_file).name}: {str(e)}")

            self.batch_progress.setValue(idx + 1)
            QApplication.processEvents()

        self.batch_run_btn.setEnabled(True)

        status = f"Completed: {success}/{len(self.batch_pairs)} pairs processed successfully."
        if errors:
            status += f"\n{len(errors)} error(s):\n" + "\n".join(errors[:5])
        self.batch_status.setText(status)
        self.batch_status.setStyleSheet("color: green;" if not errors else "color: orange;")

        if errors:
            QMessageBox.warning(self, "Batch Complete with Errors", status)
        else:
            QMessageBox.information(self, "Batch Complete", status)

    def _process_and_export_pair(self, p_file, rho_file, output_name, threshold, invert):
        """Process a single P-RHO pair and export .edge and .xlsx files."""
        out_dir = Path(p_file).parent

        p_df = pd.read_csv(p_file, sep="\t", header=1)
        rho_df = pd.read_csv(rho_file, sep="\t", header=1)

        p_df = p_df.apply(pd.to_numeric, errors='coerce')
        rho_df = rho_df.apply(pd.to_numeric, errors='coerce')

        rho_matrix = rho_df.copy()
        if invert:
            rho_matrix = rho_matrix * (-1)

        tril_mask = np.tril(np.ones(p_df.shape), k=0).astype(bool)

        p_filtered = pd.DataFrame(
            np.where(tril_mask, p_df.values, np.nan),
            index=p_df.index, columns=p_df.columns
        )
        rho_filtered = pd.DataFrame(
            np.where(tril_mask, rho_matrix.values, np.nan),
            index=rho_df.index, columns=rho_df.columns
        )

        p_filtered = p_filtered.where((p_filtered < threshold) & (p_filtered > 0))
        mask = p_filtered.notna() & rho_filtered.notna()
        p_filtered = p_filtered.where(mask)
        rho_filtered = rho_filtered.where(mask)

        # Create table
        rows = []
        for i in range(len(p_filtered)):
            for j in range(len(p_filtered.columns)):
                p_val = p_filtered.iloc[i, j]
                rho_val = rho_filtered.iloc[i, j]
                if pd.notna(p_val) and pd.notna(rho_val):
                    r1 = p_filtered.index[i]
                    r2 = p_filtered.columns[j]
                    if isinstance(r1, (int, float)) and not pd.isna(r1):
                        r1 = self.region_names[int(r1)] if int(r1) < len(self.region_names) else str(r1)
                    if isinstance(r2, (int, float)) and not pd.isna(r2):
                        r2 = self.region_names[int(r2)] if int(r2) < len(self.region_names) else str(r2)
                    if str(r2).startswith('Unnamed'):
                        continue
                    rows.append({
                        'Region1': str(r1), 'Region2': str(r2),
                        'P_Values': p_val, 'RHO_Values': rho_val
                    })

        final_table = pd.DataFrame(rows)

        # Export edge file
        rho_export = rho_matrix.copy()
        first_col = rho_export.columns[0]
        if first_col == 0 or str(first_col).startswith('Unnamed'):
            rho_export = rho_export.iloc[:, 1:]

        p_vals = p_df.copy()
        if p_vals.columns[0] == 0 or str(p_vals.columns[0]).startswith('Unnamed'):
            p_vals = p_vals.iloc[:, 1:]

        sig_mask = (p_vals < threshold) & (p_vals > 0)
        rho_export = rho_export.where(sig_mask, 0)

        d = rho_export.values
        d = np.nan_to_num(d, nan=0.0)

        edge_path = out_dir / f"{output_name}.edge"
        with open(edge_path, 'w') as f:
            for row in d:
                line = ' '.join(f"{val:.3f}" for val in row)
                f.write(line + '\n')

        xlsx_path = out_dir / f"{output_name}.xlsx"
        final_table.to_excel(xlsx_path, index=False)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PRhoProcessor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
