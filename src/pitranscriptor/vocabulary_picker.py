"""Elegir las pistas activas para la transcripción."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from pitranscriptor.vocabulary import MAX_TECHNICAL_HINTS, technical_groups


class VocabularyPicker(QDialog):
    def __init__(self, parent, translate, selected, *, suggested=()):
        super().__init__(parent)
        self.t = translate
        self.groups = technical_groups()
        self.suggested = suggested
        self.setWindowTitle(self.t("Vocabulario técnico", "Technical vocabulary"))
        self.resize(730, 480)

        body = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.t("Buscar un término…", "Find a term…"))
        self.search.setAccessibleName(self.t("Buscar un término", "Find a term"))
        filters.addWidget(self.search, 1)
        self.category = QComboBox()
        self.category.setAccessibleName(self.t("Categoría", "Category"))
        if suggested:
            self.category.addItem(self.t("Términos del guion", "Script terms"), "script")
        self.category.addItem(self.t("Todas las categorías", "All categories"))
        for group in self.groups:
            self.category.addItem(self.t(group.es, group.en), group.id)
        filters.addWidget(self.category)
        body.addLayout(filters)

        columns = QHBoxLayout()
        available_panel = QVBoxLayout()
        available_panel.addWidget(QLabel(self.t("Términos disponibles", "Available terms")))
        self.available = QListWidget()
        self.available.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        available_panel.addWidget(self.available)
        self.add_button = QPushButton(self.t("Añadir a las pistas", "Add to hints"))
        available_panel.addWidget(self.add_button)
        columns.addLayout(available_panel, 1)
        selected_panel = QVBoxLayout()
        self.count = QLabel()
        selected_panel.addWidget(self.count)
        self.active = QListWidget()
        self.active.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.active.addItems(selected)
        selected_panel.addWidget(self.active)
        self.remove_button = QPushButton(self.t("Quitar de las pistas", "Remove from hints"))
        selected_panel.addWidget(self.remove_button)
        columns.addLayout(selected_panel, 1)
        body.addLayout(columns, 1)

        custom_row = QHBoxLayout()
        custom_label = QLabel(self.t("Pista propia", "Custom hint"))
        self.custom = QLineEdit()
        self.custom.setMaxLength(100)
        self.custom.setAccessibleName(custom_label.text())
        custom_label.setBuddy(self.custom)
        self.custom_button = QPushButton(self.t("Añadir pista", "Add hint"))
        self.custom_button.setAutoDefault(False)
        custom_row.addWidget(custom_label)
        custom_row.addWidget(self.custom, 1)
        custom_row.addWidget(self.custom_button)
        body.addLayout(custom_row)

        usage = QLabel(
            self.t(
                "Las pistas activas orientan al modelo. Elige las que esperas oír en este audio.",
                "Active hints guide the model. Choose the ones you expect to hear in this audio.",
            )
        )
        usage.setWordWrap(True)
        body.addWidget(usage)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        body.addWidget(self.notice)
        actions = QDialogButtonBox()
        use = actions.addButton(self.t("Usar pistas", "Use hints"), actions.ButtonRole.AcceptRole)
        actions.addButton(self.t("Cancelar", "Cancel"), actions.ButtonRole.RejectRole)
        use.setAutoDefault(False)
        body.addWidget(actions)
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        self.search.textChanged.connect(self.refresh_available)
        self.category.currentIndexChanged.connect(self.refresh_available)
        self.custom.textChanged.connect(self.update_buttons)
        self.custom.returnPressed.connect(self.add_custom_term)
        self.custom_button.clicked.connect(self.add_custom_term)
        self.available.itemSelectionChanged.connect(self.update_buttons)
        self.active.itemSelectionChanged.connect(self.update_buttons)
        self.add_button.clicked.connect(lambda: self.add_terms())
        self.remove_button.clicked.connect(lambda: self.remove_terms())
        self.available.itemDoubleClicked.connect(lambda item: self.add_terms([item.text()]))
        self.active.itemDoubleClicked.connect(lambda item: self.remove_terms([item]))
        self.refresh_available()
        self.search.setFocus()

    def selected_terms(self):
        return tuple(self.active.item(i).text() for i in range(self.active.count()))

    def refresh_available(self):
        category = self.category.currentData()
        search = self.search.text().strip().casefold()
        selected = {term.casefold() for term in self.selected_terms()}
        candidates = (
            self.suggested
            if category == "script"
            else (
                term
                for group in self.groups
                if category is None or category == group.id
                for term in group.terms
            )
        )
        matches = [
            term
            for term in candidates
            if term.casefold() not in selected and search in term.casefold()
        ]
        self.available.clear()
        self.available.addItems(
            matches if category == "script" else sorted(matches, key=str.casefold)
        )
        self.update_buttons()

    def update_buttons(self):
        size = self.active.count()
        self.count.setText(
            self.t(
                f"Pistas activas ({size}/{MAX_TECHNICAL_HINTS})",
                f"Active hints ({size}/{MAX_TECHNICAL_HINTS})",
            )
        )
        self.add_button.setEnabled(
            size < MAX_TECHNICAL_HINTS and bool(self.available.selectedItems())
        )
        self.custom_button.setEnabled(
            size < MAX_TECHNICAL_HINTS and bool(self.custom.text().strip())
        )
        self.remove_button.setEnabled(bool(self.active.selectedItems()))

    def add_custom_term(self):
        term = " ".join(self.custom.text().split())
        if not term:
            return
        if term.casefold() in {active.casefold() for active in self.selected_terms()}:
            self.notice.setText(
                self.t("Esta pista ya está activa.", "This hint is already active.")
            )
            return
        if self.add_terms([term]):
            self.custom.clear()

    def add_terms(self, terms=None):
        if terms is None:
            terms = [item.text() for item in self.available.selectedItems()]
        if self.active.count() + len(terms) > MAX_TECHNICAL_HINTS:
            self.notice.setText(
                self.t(
                    f"Elige hasta {MAX_TECHNICAL_HINTS} pistas activas por transcripción.",
                    f"Choose up to {MAX_TECHNICAL_HINTS} active hints per transcription.",
                )
            )
            return False
        self.active.addItems(terms)
        self.notice.clear()
        self.refresh_available()
        return True

    def remove_terms(self, items=None):
        for item in self.active.selectedItems() if items is None else items:
            self.active.takeItem(self.active.row(item))
        self.notice.clear()
        self.refresh_available()
