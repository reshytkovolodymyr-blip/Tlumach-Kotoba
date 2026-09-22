"""
wizard.py
---------
Стартовий майстер на PySide6 (QDialog) — той самий функціонал, що й
у Tkinter-версії: користувач обирає мову вивчення, рівень і тему,
застосунок формує текст промпту для зовнішнього AI.

Викликається як dlg = PromptWizard(parent, ui_lang); dlg.exec() —
якщо повернуло QDialog.Accepted, парент читає dlg.result_values().
Немає окремого сценарію "закрити й нічого не перенести": і кнопка
"Далі", і закриття хрестиком (закриття вікна саме по собі трактується
Qt як reject(), тому reject() тут перевизначений так само, як accept()
— обидва зберігають поточні значення полів).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .content import WIZARD_STRINGS
from .languages import code_by_label, get_language, language_labels
from .prompt_builder import build_prompt


class PromptWizard(QDialog):
    def __init__(self, parent, ui_lang: str = "uk"):
        super().__init__(parent)
        self._t = WIZARD_STRINGS.get(ui_lang, WIZARD_STRINGS["uk"])
        self.setWindowTitle(self._t["window_title"])
        self.resize(780, 660)
        self.setMinimumSize(680, 580)

        self._result = (None, None, None)
        self._build_ui()

    def result_values(self):
        return self._result

    def _build_ui(self):
        t = self._t
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        heading = QLabel(t["heading"])
        heading.setStyleSheet("font-size: 17px; font-weight: 700;")
        layout.addWidget(heading)

        intro = QLabel(t["intro"])
        intro.setWordWrap(True)
        intro.setObjectName("hintLabel")
        layout.addWidget(intro)

        form = QFormLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(language_labels())
        self.language_combo.currentTextChanged.connect(self._sync_levels)
        form.addRow(t["label_language"], self.language_combo)

        self.level_combo = QComboBox()
        form.addRow(t["label_level"], self.level_combo)

        self.topic_edit = QLineEdit()
        self.topic_edit.returnPressed.connect(self._generate)
        form.addRow(t["label_topic"], self.topic_edit)
        layout.addLayout(form)

        self._sync_levels()
        self.topic_edit.setFocus()

        generate_btn = QPushButton(t["btn_generate"])
        generate_btn.setObjectName("primary")
        generate_btn.clicked.connect(self._generate)
        layout.addWidget(generate_btn)

        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        layout.addWidget(self.prompt_text, 1)

        bottom = QHBoxLayout()
        copy_btn = QPushButton(t["btn_copy"])
        copy_btn.setObjectName("primary")
        copy_btn.clicked.connect(self._copy)
        bottom.addWidget(copy_btn)
        bottom.addStretch(1)
        next_btn = QPushButton(t["btn_next"])
        next_btn.setObjectName("primary")
        next_btn.clicked.connect(self._continue)
        bottom.addWidget(next_btn)
        layout.addLayout(bottom)

    def _sync_levels(self):
        code = code_by_label(self.language_combo.currentText())
        levels = get_language(code).levels
        self.level_combo.clear()
        self.level_combo.addItems(levels)

    def _generate(self):
        code = code_by_label(self.language_combo.currentText())
        level = self.level_combo.currentText()
        topic = self.topic_edit.text()
        self.prompt_text.setPlainText(build_prompt(code, level, topic))

    def _copy(self):
        text = self.prompt_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, self.windowTitle(), self._t["copy_first_generate"])
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, self.windowTitle(), self._t["copied_ok"])

    def _collect_values(self):
        code = code_by_label(self.language_combo.currentText())
        level = self.level_combo.currentText()
        topic = self.topic_edit.text()
        self._result = (code, level, topic)

    def _continue(self):
        self._collect_values()
        self.accept()

    def reject(self):
        # Закриття хрестиком поводиться так само, як "Далі" — завжди
        # переносить поточні значення полів, а не відкидає їх.
        self._collect_values()
        self.done(QDialog.Accepted)
