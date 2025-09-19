from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QWidget, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton
from PyQt6.QtCore import Qt
import json

class ColumnConfigDialog(QDialog):
    """Dialog to edit columns configuration for grids.

    Expects a list of column dicts: {id,label,visible,sortable} passed via `columns`.
    """
    def __init__(self, columns=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configura colonne")
        self.resize(500, 400)
        self._columns = columns or []

        self.layout = QVBoxLayout(self)

        # List of columns with controls
        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

        for col in self._columns:
            item = QListWidgetItem()
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(4, 4, 4, 4)
            chk = QCheckBox()
            chk.setChecked(bool(col.get('visible', True)))
            lbl = QLabel(col.get('id'))
            edt = QLineEdit(col.get('label', col.get('id')))
            sort_chk = QCheckBox('Sortable')
            sort_chk.setChecked(bool(col.get('sortable', False)))
            hl.addWidget(chk)
            hl.addWidget(lbl)
            hl.addWidget(edt)
            hl.addWidget(sort_chk)
            hl.addStretch()
            item.setSizeHint(w.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)
            # store widgets for retrieval
            item._widgets = (chk, edt, sort_chk, col.get('id'))

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton('Salva')
        self.cancel_btn = QPushButton('Annulla')
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_columns(self):
        cols = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            chk, edt, sort_chk, cid = item._widgets
            cols.append({
                'id': cid,
                'label': edt.text().strip() or cid,
                'visible': bool(chk.isChecked()),
                'sortable': bool(sort_chk.isChecked())
            })
        return cols
