#!/usr/bin/python3

import sys
import os
import subprocess
import re
import yaml
import locale
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLineEdit, QListWidget, QFontDialog,
                             QVBoxLayout, QHBoxLayout, QWidget, QSystemTrayIcon, QSplitter, QLabel,
                             QMenu, QAction, QInputDialog, QMessageBox, QPushButton, QGridLayout)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QFile, QTextStream, QDir, Qt, QEvent, QTranslator

# Pfad zum Arbeitsverzeichnis festlegen
arbeitsverzeichnis = os.path.expanduser('/usr/share/x-live/notes/')
os.chdir(arbeitsverzeichnis)


class NotizVerwaltung(QMainWindow):
    def __init__(self):
        super().__init__()

        # Fensterkonfiguration
        self.setWindowTitle("Notizverwaltung")
        self.setWindowIcon(QIcon("./notiz.png"))
        self.setGeometry(100, 100, 800, 600)
        self.current_note_file = None
        self.text_changed = False
        self.notes_dir = os.path.expanduser("~/x-live/notes/")
        self.settings_file = os.path.expanduser("~/.x-live/settings/notes.yml")
        self.settings_dir = os.path.expanduser("~/.x-live/settings/")

        # Notizen-Verzeichnis prüfen oder erstellen
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)

        # Hauptlayout
        layout = QVBoxLayout()

        # Menü erstellen
        self.button_menu = QMenu()
        self.list_menu = QMenu()
        self.init_menu()

        # Buttons 
        self.init_buttons(layout)

        # Notizenliste, Suchleiste und Textanzeige
        self.init_splitter(layout)

        # Hauptwidget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Tray-Icon erstellen
        self.init_tray_icon()


        # Signale verbinden
        self.listWidget.itemClicked.connect(self.on_note_selected)
        self.textEdit.textChanged.connect(self.on_text_changed)
        self.hide()

        # Notizen und Fenstereinstellungen laden
        self.load_notes()
        self.load_window_settings()
        self.check_font()

        # Themenanpassung
        self.background_color()

    def init_menu(self):
        """Erstellt ein neues Menü für die Notizverwaltung."""
        
        # Aktionen für das Menü
        new_action = QAction("Neue Notiz", self)
        new_action.setIcon(QIcon("./new.png"))
        new_action.triggered.connect(self.add_note)
        self.button_menu.addAction(new_action)

        rename_action = QAction("Notiz umbenennen", self)
        rename_action.setIcon(QIcon("./rename.png"))
        rename_action.triggered.connect(self.rename_note)
        self.button_menu.addAction(rename_action)
        self.list_menu.addAction(rename_action)

        delete_action = QAction("Notiz löschen", self)
        delete_action.setIcon(QIcon("./delete.png"))
        delete_action.triggered.connect(self.delete_note)
        self.button_menu.addAction(delete_action)
        self.list_menu.addAction(delete_action)

        self.button_menu.addSeparator()

        self.font_action = QAction("Schriftart", self)
        self.font_action.setIcon(QIcon("./font.png"))
        self.font_action.triggered.connect(self.change_font)
        self.button_menu.addAction(self.font_action)

        self.button_menu.addSeparator()

        exit_action = QAction("Beenden", self)
        exit_action.setIcon(QIcon("./close.png"))
        exit_action.triggered.connect(self.quit_app)
        self.button_menu.addAction(exit_action)

    def init_buttons(self, layout):
        """Erstellt Buttons und eine Suchleiste."""
        button_layout = QHBoxLayout()

        self.new_button = QPushButton()
        self.new_button.setIcon(QIcon("./list.png"))
        self.new_button.clicked.connect(self.splitter_toogle)
        button_layout.addWidget(self.new_button)

        self.menu_button = QPushButton("Menü")
        self.menu_button.setIcon(QIcon("./menu.png"))
        self.menu_button.setMenu(self.button_menu)
        button_layout.addWidget(self.menu_button)

        button_layout.addStretch(10000)

        self.about_button = QPushButton("Über")
        self.about_button.setIcon(QIcon("./about.png"))
        self.about_button.clicked.connect(self.show_about_dialog)
        button_layout.addWidget(self.about_button)

        button_layout.addStretch(5)
        layout.addLayout(button_layout)

    def init_splitter(self, layout):
        """Erstellt die Aufteilung zwischen Liste und Textanzeige."""
        left_layout = QVBoxLayout() 
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Notizen durchsuchen...")
        self.search_input.textChanged.connect(self.filter_notes)
        left_layout.addWidget(self.search_input)
        self.listWidget = QListWidget()         
        left_layout.addWidget(self.listWidget)
        self.textEdit = QTextEdit()
        self.textEdit.setAcceptRichText(False) 
        self.splitter = QSplitter()
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.textEdit)
        self.splitter.setSizes([30, 950])
        layout.addWidget(self.splitter)
        # Rechtsklick für das QListWidget einrichten
        self.listWidget.setContextMenuPolicy(3)  # CustomContextMenu
        self.listWidget.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        # Menü an der Position für das QListWidget anzeigen
        self.list_menu.exec_(self.mapToGlobal(pos))

    def splitter_toogle(self):
        if self.splitter.sizes()[0] != 0:
            self.splitter.setSizes([0, self.splitter.sizes()[1]])
        else:
            self.listWidget.adjustSize()
            self.splitter.setSizes([self.listWidget.width(), self.splitter.sizes()[1]])
            self.listWidget.adjustSize()
            self.splitter.setSizes([self.listWidget.width(), self.splitter.sizes()[1]])

    def init_tray_icon(self):
        """Erstellt ein Tray-Icon mit Menü."""
        self.trayIcon = QSystemTrayIcon(QIcon("./notiz.png"), self)
        trayMenu = QMenu(self)

        show_action = QAction("Öffnen", self)
        show_action.triggered.connect(self.show)
        trayMenu.addAction(show_action)

        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.quit_app)
        trayMenu.addAction(quit_action)

        self.trayIcon.setContextMenu(trayMenu)
        self.trayIcon.activated.connect(self.toggle_window)
        self.trayIcon.show()

    # Funktion zum Löschen der ausgewählten Notiz
    def delete_note(self):
        current_item = self.listWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Fehler", "Keine Notiz ausgewählt.")
            return

        note_file = current_item.text() + ".txt"
        full_path = os.path.join(self.notes_dir, note_file)

        # Bestätigungsdialog vor dem Löschen
        reply = QMessageBox.question(self, "Bestätigung", f"Soll die Notiz '{current_item.text()}' wirklich gelöscht werden?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # Datei löschen
                os.remove(full_path)

                # Aktuelle Zeile in der Liste merken
                current_row = self.listWidget.row(current_item)

                # Element aus der Liste entfernen
                self.listWidget.takeItem(current_row)

                # Notiz darüber oder darunter auswählen
                if self.listWidget.count() > 0:
                    # Wähle die nächste Notiz aus (oder die vorherige, falls es keine nächste gibt)
                    if current_row < self.listWidget.count():
                        self.listWidget.setCurrentRow(current_row)
                    else:
                        self.listWidget.setCurrentRow(current_row - 1)

                    # Lade die neu ausgewählte Notiz
                    selected_item = self.listWidget.currentItem()
                    if selected_item:
                        self.load_note(selected_item.text() + ".txt")
                else:
                    # Wenn keine Notizen mehr vorhanden sind, Textfeld sperren und leeren
                    self.textEdit.clear()
                    self.textEdit.setReadOnly(True)
                    QMessageBox.information(self, "Keine Notizen", "Es sind keine Notizen mehr vorhanden.")
            except FileNotFoundError:
                QMessageBox.warning(self, "Fehler", f"Die Datei '{note_file}' konnte nicht gefunden werden.")

    def load_notes(self):
        # Notizen aus dem Verzeichnis ~/x-live/notes/ laden und in der Liste anzeigen
        self.listWidget.clear()
        self.note_files = [f for f in sorted(os.listdir(self.notes_dir)) if f.endswith(".txt")]


        if self.note_files:
            # Notizen ohne Endung anzeigen
            for file_name in self.note_files:
                self.listWidget.addItem(file_name[:-4])  # ".txt" entfernen
            
            # Erste Notiz automatisch auswählen und laden
            self.listWidget.setCurrentRow(0)
            self.load_note(self.note_files[0])

    def on_note_selected(self, item):
        # theme holen und aktivieren
        self.background_color()
        # Prüft, ob die aktuelle Notiz gespeichert wurde, bevor gewechselt wird
        if self.text_changed:
            self.save_note()

        # Neue Notiz laden
        note_file = item.text() + ".txt"  # ".txt" wieder hinzufügen
        self.load_note(note_file)

    def load_note(self, note_file):
        # Inhalt der ausgewählten Notiz laden
        self.current_note_file = os.path.join(self.notes_dir, note_file)
        file = QFile(self.current_note_file)
        if file.open(QFile.ReadOnly | QFile.Text):
            text_stream = QTextStream(file)
            self.textEdit.blockSignals(True)  # Deaktiviert Signale beim Setzen des Textes
            self.textEdit.setPlainText(text_stream.readAll())
            self.textEdit.blockSignals(False)  # Reaktiviert Signale
        file.close()
        self.text_changed = False  # Text ist noch nicht geändert worden
        self.setWindowTitle(f"Notizverwaltung - {note_file.replace(".txt","")}")

    def on_text_changed(self):
        # Markiert den Text als geändert
        self.text_changed = True

    def save_note(self):
        # Speichert die geänderte Notiz in die Datei
        if self.current_note_file:
            file = QFile(self.current_note_file)
            if file.open(QFile.WriteOnly | QFile.Text):
                text_stream = QTextStream(file)
                text_stream << self.textEdit.toPlainText()
            file.close()
            self.text_changed = False  # Markiert den Text als gespeichert

    def add_note(self):
        # Neue Notiz erstellen
        name, ok = QInputDialog.getText(self, "Neue Notiz", "Name der Notiz:")
        if ok and name:
            note_file = name + ".txt"
            full_path = os.path.join(self.notes_dir, note_file)
            if os.path.exists(full_path):
                QMessageBox.warning(self, "Fehler", "Eine Notiz mit diesem Namen existiert bereits.")
            else:
                # Datei für die neue Notiz erstellen und in der Liste hinzufügen
                self.listWidget.addItem(name)
                self.filter_notes()
                file = QFile(full_path)
                if file.open(QFile.WriteOnly | QFile.Text):
                    file.write(b"")  # Leere Notiz erstellen (b"" ist ein Byte-String)
                file.close()


    def rename_note(self):
        current_item = self.listWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Fehler", "Keine Notiz ausgewählt.")
            return

        old_name = current_item.text()
        old_file_path = os.path.join(self.notes_dir, f"{old_name}.txt")

        # Benutzereingabe für den neuen Dateinamen
        new_name, ok = QInputDialog.getText(self, "Notiz umbenennen", "Neuer Name:", text=old_name)
        
        if ok and new_name:
            new_file_path = os.path.join(self.notes_dir, f"{new_name}.txt")
            try:
                # Datei umbenennen
                os.rename(old_file_path, new_file_path)

                # Den Listeneintrag aktualisieren
                current_item.setText(new_name)

                # Erfolgsnachricht anzeigen
                QMessageBox.information(self, "Erfolg", f"Die Notiz wurde erfolgreich umbenannt in '{new_name}'.")
            except FileNotFoundError:
                QMessageBox.warning(self, "Fehler", "Die Datei konnte nicht gefunden werden.")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Beim Umbenennen ist ein Fehler aufgetreten: {str(e)}")
            self.load_notes()


    def filter_notes(self):
        """ Die Liste der Notizen basierend auf der Benutzereingabe filtern """
        filter_text = self.search_input.text().lower()
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            item.setHidden(filter_text not in item.text().lower())



    def toggle_window(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                # theme holen und aktivieren
                self.background_color()
                # Widget anzeigen
                self.restore_from_tray()
                # Widget in den vordergrund holen
                self.raise_()

    def quit_app(self):
        # Vor dem Beenden sicherstellen, dass die aktuelle Notiz gespeichert wird
        if self.text_changed:
            self.save_note()
        self.save_window_settings()  # Fenster- und Splitter-Position speichern
        QApplication.quit()
        
    def restore_from_tray(self):
        self.showNormal()  # Wiederherstellen des Fensters

    def changeEvent(self, event):
        # Überprüfen, ob das Fenster minimiert wurde
        if event.type() == QEvent.WindowStateChange and self.windowState() == Qt.WindowMinimized:
            self.hide()  # Fenster verstecken
            event.ignore()  # Minimierung verhindern und ins Tray verschieben



    def closeEvent(self, event):
        # Beim Schließen des Programms speichern, falls nötig
        if self.text_changed:
            self.save_note()
        self.save_window_settings()  # Fenster- und Splitter-Position speichern
        event.ignore()
        self.hide()
        
    def save_window_settings(self):
        current_font = self.textEdit.font()
        if not os.path.exists(self.settings_dir):
            os.makedirs(self.settings_dir)

        settings = {
            'geometry': self.saveGeometry().data().hex(),   # Speichert die Geometrie
            'state': self.saveState().data().hex(),         # Speichert den Zustand
            'splitter_sizes': self.splitter.sizes(),        # Speichert die Größen des Splitters
            'font': {
                'family': current_font.family(),
                'size': current_font.pointSize(),
                'bold': current_font.bold(),
                'italic': current_font.italic()
            }  # Speichert die Schriftart als Dictionary
        }
        with open(self.settings_file, 'w') as file:
            yaml.dump(settings, file)

    def load_window_settings(self):
        """Lädt die Fenster- und Splitter-Positionen aus der YAML-Datei."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as file:
                settings = yaml.load(file, Loader=yaml.FullLoader)
                if settings:
                    self.restoreGeometry(bytes.fromhex(settings['geometry']))   # Stelle die Geometrie wieder her
                    self.restoreState(bytes.fromhex(settings['state']))         # Stelle den Zustand wieder her
                    self.splitter.setSizes(settings['splitter_sizes'])          # Stelle die Größen des Splitters wieder her
                    
                    # Schriftart wiederherstellen
                    font_data = settings.get('font', {})
                    if font_data:
                        font = QFont()
                        font.setFamily(font_data.get('family', ''))
                        font.setPointSize(font_data.get('size', 12))  # Standardgröße 12 pt
                        font.setBold(font_data.get('bold', False))
                        font.setItalic(font_data.get('italic', False))
                        self.textEdit.setFont(font)
  
        
    def check_font(self):
        # Aktuelle Schriftart des Labels abfragen
        current_font = self.textEdit.font()
        font_name = current_font.family()
        font_size = current_font.pointSize()
        is_bold = current_font.bold()
        is_italic = current_font.italic()

        # Stiltext erstellen
        style_text = []
        if is_bold:
            style_text.append("Fett")
        if is_italic:
            style_text.append("Kursiv")
        if not style_text:
            style_text.append("")
            #style_text.append("Normal")
        style_text = " und ".join(style_text)

        # Schriftinformationen anzeigen
        self.font_action.setText(f"Schriftart: {font_name} {style_text} - {font_size}px")

    def change_font(self):
        # Schriftart ändern
        font, ok = QFontDialog.getFont(self.textEdit.font(), self)  # Aktuelle Schriftart als Standard übergeben
        if ok:
            self.textEdit.setFont(font)
        self.check_font()
        
    # Farbprofil abrufen und anwenden

    def get_current_theme(self):
        try:
            # Versuche, das Theme mit xfconf-query abzurufen
            result = subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/ThemeName'], capture_output=True, text=True)
            theme_name = result.stdout.strip()
            if theme_name:
                return theme_name
        except FileNotFoundError:
            print("xfconf-query nicht gefunden. Versuche gsettings.")
        except Exception as e:
            print(f"Error getting theme with xfconf-query: {e}")
        try:
            # Fallback auf gsettings, falls xfconf-query nicht vorhanden ist
            result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], capture_output=True, text=True)
            theme_name = result.stdout.strip().strip("'")
            if theme_name:
                return theme_name
        except Exception as e:
            print(f"Error getting theme with gsettings: {e}")
    
        return None

    def extract_color_from_css(self,css_file_path, color_name):
        try:
            with open(css_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Muster zum Finden der Farbe
                pattern = r'{}[\s:]+([#\w]+)'.format(re.escape(color_name))
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
                return None
        except IOError as e:
            print(f"Error reading file: {e}")
            return None
            
            
    def background_color(self):
        theme_name = self.get_current_theme()
        if theme_name:
            # Pfad zur GTK-CSS-Datei des aktuellen Themes
            css_file_path = f'/usr/share/themes/{theme_name}/gtk-3.0/gtk.css'
            if os.path.exists(css_file_path):
                bcolor = self.extract_color_from_css(css_file_path, ' background-color')
                color = self.extract_color_from_css(css_file_path, ' color')
                self.setStyleSheet("""
                            QPushButton {
                                color: """ + color + """;  /* Farbe */
                                background-color: """ + bcolor + """;    /* Hintergrundfarbe  */

                            }
                            QPushButton::hover {
                                color: """ + bcolor + """;  /* Farbe */
                                background-color: """ + color + """;    /* Hintergrundfarbe  */

                            }

                            QMenu {
                                color: """ + bcolor + """;  /* Farbe */
                                background-color: """ + color + """;    /* Hintergrundfarbe  */
                                border: 3px solid """ + bcolor + """; /* Rahmen */
                                border-radius: 3px;
                            }
                            QMenu::item {
                                padding: 2px 8px;        /* Innenabstand */
                                margin: 0px;             /* Abstand zwischen Items */
                            }
                            QMenu::item:disabled {
                                color: #20""" + color.replace('#','') + """;  /* Farbe */
                                background-color: """ + bcolor + """;    /* Hintergrundfarbe  */
                            }
                            QMenu::item:selected {       /* Hover-Effekt */
                                color: """ + bcolor + """;  /* Farbe */
                                background-color: """ + color + """;    /* Hintergrundfarbe  */
                            }
                            QMenu::separator {
                                height: 2px;
                                background: """ + color + """;
                                margin: 2px 2px;
                            }
                            QWidget {
                                color: """ + color + """;  /* Farbe */
                                background-color: """ + bcolor + """;    /* Hintergrundfarbe  */

                            }
                            QTextEdit {
                                color: """ + bcolor + """;  /* Farbe */
                                border-color: """ + color + """; /* Rahmenfarbe */
                                background-color: """ + color + """;    /* Hintergrundfarbe  */
                                border-radius: 5px; /* abgerundete Ecken */

                            }
                        """)

            else:
                print(f"CSS file not found: {css_file_path}")
        else:
            print("Unable to determine the current theme.")


    # Ermittlung der Benutzersprache
    def get_user_language(self):
        return os.environ.get('LANG', 'en_US')

    def show_about_dialog(self):
        # Extrahiere die Version aus der Versionsermittlungsfunktion
        version = self.get_version_info()
        language = self.get_user_language()

        # Setze den Text je nach Sprache
        if language.startswith("de"):
            title = "Über X-Live Notes"
            text = (f"X-Live Notes<br><br>"
                    f"Autor: VerEnderT aka F. Maczollek<br>"
                    f"Webseite: <a href='https://github.com/verendert/x-live-notes'>https://github.com/verendert/x-live-notes</a><br>"
                    f"Version: {version}<br><br>"
                    f"Copyright © 2024 VerEnderT<br>"
                    f"Dies ist freie Software; Sie können es unter den Bedingungen der GNU General Public License Version 3 oder einer späteren Version weitergeben und/oder modifizieren.<br>"
                    f"Dieses Programm wird in der Hoffnung bereitgestellt, dass es nützlich ist, aber OHNE JEDE GARANTIE; sogar ohne die implizite Garantie der MARKTGÄNGIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.<br><br>"
                    f"Sie sollten eine Kopie der GNU General Public License zusammen mit diesem Programm erhalten haben. Wenn nicht, siehe <a href='https://www.gnu.org/licenses/'>https://www.gnu.org/licenses/</a>.")
        else:
            title = "About X-Live Notes"
            text = (f"X-Live Notes<br><br>"
                    f"Author: VerEnderT aka F. Maczollek<br>"
                    f"Website: <a href='https://github.com/verendert/x-live-notes'>https://github.com/verendert/x-live-notes</a><br>"
                    f"Version: {version}<br><br>"
                    f"Copyright © 2024 VerEnderT<br>"
                    f"This is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License Version 3 or any later version.<br>"
                    f"This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.<br><br>"
                    f"You should have received a copy of the GNU General Public License along with this program. If not, see <a href='https://www.gnu.org/licenses/'>https://www.gnu.org/licenses/</a>.")
        
        # Über Fenster anzeigen
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setWindowIcon(QIcon("./notiz.png"))
        msg_box.setTextFormat(Qt.RichText)  # Setze den Textformatierungsmodus auf RichText (HTML)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def get_version_info(self):
        try:
            result = subprocess.run(['apt', 'show', 'x-live-editcsv'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        except Exception as e:
            print(f"Fehler beim Abrufen der Version: {e}")
        return "Unbekannt"



  
if __name__ == "__main__":
    app = QApplication(sys.argv)

    system_language = locale.getdefaultlocale()[0]
    translator = QTranslator()
    # Überprüfe Systemsprache auf Deutsch 
    if system_language.startswith('de'):
        # Deutsche Übersetzung laden
        if translator.load("/usr/share/qt5/translations/qtbase_de.qm"):
            app.installTranslator(translator)
        else:
            print("Fehler: Deutsche Übersetzungsdatei nicht gefunden")
    else:
        # Englische Übersetzung laden
        if translator.load("/usr/share/qt5/translations/qtbase_en.qm"):
            app.installTranslator(translator)
        else:
            print("Fehler: Englische Übersetzungsdatei nicht gefunden")

    window = NotizVerwaltung()
    sys.exit(app.exec())