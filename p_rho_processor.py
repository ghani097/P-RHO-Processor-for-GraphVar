"""
P-RHO Matrix Processor - PyQt5 GUI
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QSlider, QCheckBox, QLineEdit, QGroupBox, QMessageBox, QFrame
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

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
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


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PRhoProcessor()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
