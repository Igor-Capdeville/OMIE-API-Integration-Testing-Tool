import sys
import json
import os
#import re
import traceback
import io
from contextlib import redirect_stdout, redirect_stderr
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QComboBox, 
                             QLabel, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, 
                             QTextEdit, QProgressBar, QFileDialog, QMessageBox,
                             QFrame, QScrollArea, QSizePolicy, QToolButton, 
                             QInputDialog, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor
import config
import main

class CollapsibleBox(QWidget):
    """Custom collapsible box widget with smooth animation and proper sizing"""
    
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)
        
        # Main vertical layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header widget (always visible)
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toggle button with arrow
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setAutoRaise(True)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont('Arial', 12, QFont.Bold))
        
        # Add to header layout
        self.header_layout.addWidget(self.toggle_button)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        
        # Content widget (collapsible)
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.header_widget)
        self.main_layout.addWidget(self.content_widget)
        
        # Connect signals
        self.toggle_button.clicked.connect(self.toggle_content)
        
    def toggle_content(self, checked):
        """Toggle the visibility of the content area"""
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content_widget.setVisible(checked)
        self.adjustSize()
        
        # Emit signal to parent to adjust layout if needed
        self.parent().adjustSize() if self.parent() else None
        
    def set_content_layout(self, layout):
        """Set the layout for the content area"""
        # Clear any existing layout
        if self.content_widget.layout():
            while self.content_widget.layout().count():
                item = self.content_widget.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.content_widget.layout().deleteLater()
            
        # Set new layout
        self.content_widget.setLayout(layout)

class ApiWorker(QThread):
    """Worker thread for API calls to prevent UI freezing"""
    update_progress = pyqtSignal(int, int)  # current_page, total_pages
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    log_output = pyqtSignal(str)  # New signal for terminal output

    def __init__(self, call_type, credentials):
        super().__init__()
        self.call_type = call_type
        self.credentials = credentials

    def run(self):
        try:
            # Capture stdout and stderr
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                all_results = []
                current_page = 1
                
                while True:
                    result = main.api_omie(call=self.call_type, page=current_page, credentials=self.credentials)
                    if not result:
                        break

                    all_results.append(result)
                    
                    # Get total pages from response
                    total_pages = result.get('total_de_paginas', 0)
                    self.update_progress.emit(current_page, total_pages)
                    
                    if current_page >= total_pages:
                        break
                        
                    current_page += 1
            
            # Emit terminal output
            terminal_output = stdout_buffer.getvalue() + stderr_buffer.getvalue()
            self.log_output.emit(terminal_output)
            
            # Check if we got any actual results
            if all_results:
                self.finished.emit(all_results)
            else:
                # If we got an empty list but no exception, show as error
                self.error.emit("Empty response - No data returned from API")
                
        except Exception as e:
            error_detail = traceback.format_exc()
            self.error.emit(f"{str(e)}\n\n{error_detail}")
            
            # Still emit any terminal output we captured
            terminal_output = stdout_buffer.getvalue() + stderr_buffer.getvalue()
            self.log_output.emit(terminal_output)

class ScrollableArea(QScrollArea):
    """Custom scrollable area that properly handles resizing"""
    
    def __init__(self, parent=None):
        super(ScrollableArea, self).__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
    def sizeHint(self):
        """Return a size hint that adapts to the content"""
        widget = self.widget()
        if widget:
            return QSize(widget.sizeHint().width() + self.verticalScrollBar().sizeHint().width(),
                        min(500, widget.sizeHint().height() + self.horizontalScrollBar().sizeHint().height()))
        return super().sizeHint()

class OmieApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.credentials = None
        self.worker = None
        self.output_file = None
        self.saved_profiles = {}
        self.credentials_file = "credentials.json"
        self.log_entries = []
        self.load_saved_profiles()
        self.initUI()
        
    def load_saved_profiles(self):
        """Load saved credential profiles from file"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    self.saved_profiles = json.load(f)
        except Exception as e:
            print(f"Error loading profiles: {e}")
            self.saved_profiles = {}
        
    def save_profiles(self):
        """Save credential profiles to file"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.saved_profiles, f, indent=4)
        except Exception as e:
            print(f"Error saving profiles: {e}")
            
    def initUI(self):
        # Set window properties
        self.setWindowTitle('OMIE API Integration Tool')
        self.setMinimumSize(900, 700)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create main tab
        self.main_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "Main")
        
        # Create log tab
        self.log_tab = QWidget()
        self.tab_widget.addTab(self.log_tab, "Log")
        
        # Setup main tab UI
        self.setup_main_tab()
        
        # Setup log tab UI
        self.setup_log_tab()
        
    def setup_main_tab(self):
        # Create main scrollable area
        main_scroll = ScrollableArea()
        
        # Create main container widget
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Set the main container as the scroll area's widget
        main_scroll.setWidget(main_container)
        
        # Set layout for main tab
        main_tab_layout = QVBoxLayout(self.main_tab)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        main_tab_layout.addWidget(main_scroll)
        
        # Add title
        title_label = QLabel('OMIE API Integration Tool')
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel('Connect to OMIE API and retrieve data')
        desc_label.setFont(QFont('Arial', 10))
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # Add separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Collapsible credentials box
        self.cred_box = CollapsibleBox("API Credentials")
        cred_layout = QVBoxLayout()
        cred_layout.setContentsMargins(15, 15, 15, 15)
        cred_layout.setSpacing(15)
        
        # Credential profiles section
        profiles_layout = QVBoxLayout()
        profiles_header = QHBoxLayout()
        profiles_label = QLabel("Saved Profiles:")
        profiles_label.setFont(QFont('Arial', 10, QFont.Bold))
        profiles_header.addWidget(profiles_label)
        profiles_layout.addLayout(profiles_header)
        
        # Profile selector layout (make it responsive)
        profiles_selector = QVBoxLayout()
        
        # Profile dropdown
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(250)
        self.profile_combo.currentIndexChanged.connect(self.load_selected_profile)
        profiles_selector.addWidget(self.profile_combo)
        
        # Profile action buttons in a responsive grid
        profile_actions = QHBoxLayout()
        profile_actions.setSpacing(10)
        
        load_profile_btn = QPushButton("Load")
        load_profile_btn.clicked.connect(self.load_selected_profile)
        load_profile_btn.setFixedWidth(80)
        profile_actions.addWidget(load_profile_btn)
        
        save_profile_btn = QPushButton("Save Current")
        save_profile_btn.clicked.connect(self.save_as_profile)
        profile_actions.addWidget(save_profile_btn)
        
        delete_profile_btn = QPushButton("Delete")
        delete_profile_btn.clicked.connect(self.delete_profile)
        delete_profile_btn.setFixedWidth(80)
        profile_actions.addWidget(delete_profile_btn)
        
        profiles_selector.addLayout(profile_actions)
        profiles_layout.addLayout(profiles_selector)
        cred_layout.addLayout(profiles_layout)
        
        # Add separator line
        cred_sep = QFrame()
        cred_sep.setFrameShape(QFrame.HLine)
        cred_sep.setFrameShadow(QFrame.Sunken)
        cred_layout.addWidget(cred_sep)
        
        # Credential inputs - made more responsive
        # API Key input
        key_layout = QVBoxLayout()
        key_label = QLabel('App Key:')
        key_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.key_input = QLineEdit()
        self.key_input.setMinimumHeight(30)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        cred_layout.addLayout(key_layout)
        
        # API Secret input
        secret_layout = QVBoxLayout()
        secret_label = QLabel('App Secret:')
        secret_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.secret_input = QLineEdit()
        self.secret_input.setEchoMode(QLineEdit.Password)
        self.secret_input.setMinimumHeight(30)
        secret_layout.addWidget(secret_label)
        secret_layout.addWidget(self.secret_input)
        cred_layout.addLayout(secret_layout)
        
        # Apply credentials button
        apply_cred_btn = QPushButton('Apply Credentials')
        apply_cred_btn.clicked.connect(self.apply_credentials)
        cred_layout.addWidget(apply_cred_btn)
        
        # Set content to collapsible box
        self.cred_box.set_content_layout(cred_layout)
        main_layout.addWidget(self.cred_box)
        
        # Add another separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line2)
        
        # API Call section
        call_layout = QVBoxLayout()
        call_title = QLabel('API Call Settings')
        call_title.setFont(QFont('Arial', 12, QFont.Bold))
        call_layout.addWidget(call_title)
        
        # Active credentials display
        self.active_cred_label = QLabel('No active credentials')
        self.active_cred_label.setStyleSheet("color: #777; font-style: italic;")
        call_layout.addWidget(self.active_cred_label)
        
        # Call type selection - made more responsive
        call_type_layout = QVBoxLayout()
        call_type_label = QLabel('Call Type:')
        call_type_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.call_type_combo = QComboBox()
        self.call_type_combo.setMinimumHeight(30)
        
        # Populate combobox with call types from config
        for call_name in config.calltype.keys():
            self.call_type_combo.addItem(call_name)
            
        call_type_layout.addWidget(call_type_label)
        call_type_layout.addWidget(self.call_type_combo)
        call_layout.addLayout(call_type_layout)
        
        # Execute API call button
        self.execute_btn = QPushButton('Execute API Call')
        self.execute_btn.setMinimumHeight(40)
        self.execute_btn.clicked.connect(self.execute_api_call)
        call_layout.addWidget(self.execute_btn)
        
        # View log button
        view_log_btn = QPushButton('View Terminal Log')
        view_log_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        call_layout.addWidget(view_log_btn)
        
        main_layout.addLayout(call_layout)
        
        # Progress section
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel('Ready')
        self.progress_label.setFont(QFont('Arial', 10, QFont.Bold))
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # Results section
        results_layout = QVBoxLayout()
        results_title = QLabel('Results')
        results_title.setFont(QFont('Arial', 12, QFont.Bold))
        results_layout.addWidget(results_title)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(200)
        results_layout.addWidget(self.results_text)
        
        # Save results button
        self.save_btn = QPushButton('Save Results')
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setEnabled(False)
        results_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(results_layout)
        
        # Initialize profiles dropdown
        self.update_profile_dropdown()
        
        # Try to load saved credentials from config
        self.load_credentials_from_config()
    
    def setup_log_tab(self):
        # Create layout for log tab
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(15)
        
        # Add header
        header_layout = QHBoxLayout()
        
        log_title = QLabel('Terminal Log')
        log_title.setFont(QFont('Arial', 18, QFont.Bold))
        header_layout.addWidget(log_title)
        
        # Add return button
        return_btn = QPushButton('Return to Main')
        return_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        return_btn.setFixedWidth(150)
        header_layout.addWidget(return_btn)
        
        log_layout.addLayout(header_layout)
        
        # Add description
        log_desc = QLabel('This log shows the terminal output from API calls')
        log_desc.setFont(QFont('Arial', 10))
        log_layout.addWidget(log_desc)
        
        # Add separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        log_layout.addWidget(sep)
        
        # Add log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 9))  # Monospaced font for log
        self.log_text.setStyleSheet("background-color: #f0f0f0; color: #333333;")
        log_layout.addWidget(self.log_text)
        
        # Add clear log button
        clear_log_btn = QPushButton('Clear Log')
        clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_btn)

    def update_profile_dropdown(self):
        """Update the profiles dropdown with saved profiles"""
        self.profile_combo.clear()
        self.profile_combo.addItem("-- Select Profile --")
        
        # Add saved profiles to dropdown
        for profile_name in sorted(self.saved_profiles.keys()):
            self.profile_combo.addItem(profile_name)
    
    def save_as_profile(self):
        """Save current credentials as a named profile"""
        key = self.key_input.text().strip()
        secret = self.secret_input.text().strip()
        
        if not key or not secret:
            QMessageBox.warning(self, 'Missing Credentials', 
                               'Please enter both API Key and Secret')
            return
            
        # Ask for profile name
        profile_name, ok = QInputDialog.getText(self, 'Save Profile', 
                                               'Enter a name for this profile:')
        
        if ok and profile_name:
            # Save to profiles dictionary
            self.saved_profiles[profile_name] = {
                'key': key,
                'secret': secret
            }
            
            # Save to file
            self.save_profiles()
            
            # Update dropdown
            self.update_profile_dropdown()
            
            # Select the new profile
            index = self.profile_combo.findText(profile_name)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
                
            QMessageBox.information(self, 'Success', f'Profile "{profile_name}" saved successfully')
            
    def load_selected_profile(self):
        """Load the selected profile's credentials"""
        profile_name = self.profile_combo.currentText()
        
        # Skip if it's the placeholder
        if profile_name == "-- Select Profile --":
            return
            
        # Get credentials from saved profiles
        if profile_name in self.saved_profiles:
            profile = self.saved_profiles[profile_name]
            self.key_input.setText(profile['key'])
            self.secret_input.setText(profile['secret'])
            
            # Set as active credentials
            self.credentials = (profile['key'], profile['secret'])
            self.active_cred_label.setText(f"Active credentials: {profile_name}")
            self.active_cred_label.setStyleSheet("color: #2979ff; font-weight: bold;")
    
    def delete_profile(self):
        """Delete the selected profile"""
        profile_name = self.profile_combo.currentText()
        
        # Skip if it's the placeholder
        if profile_name == "-- Select Profile --":
            return
            
        # Confirm deletion
        reply = QMessageBox.question(self, 'Confirm Deletion', 
                                    f'Are you sure you want to delete the profile "{profile_name}"?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove from saved profiles
            if profile_name in self.saved_profiles:
                del self.saved_profiles[profile_name]
                
                # Save to file
                self.save_profiles()
                
                # Update dropdown
                self.update_profile_dropdown()
                
                QMessageBox.information(self, 'Success', f'Profile "{profile_name}" deleted successfully')

    def load_credentials_from_config(self):
        """Load credentials from config if they exist"""
        try:
            app_key = config.app_key
            app_secret = config.app_secret
            self.key_input.setText(app_key)
            self.secret_input.setText(app_secret)
            self.credentials = (app_key, app_secret)
            self.active_cred_label.setText("Active credentials: from config.py")
            self.active_cred_label.setStyleSheet("color: #2979ff; font-weight: bold;")
        except AttributeError:
            # No credentials found in config
            self.active_cred_label.setText("No active credentials")
            self.active_cred_label.setStyleSheet("color: #777; font-style: italic;")
    
    def apply_credentials(self):
        """Apply the current credentials"""
        key = self.key_input.text().strip()
        secret = self.secret_input.text().strip()
        
        if not key or not secret:
            QMessageBox.warning(self, 'Missing Credentials', 
                               'Please enter both API Key and Secret')
            return
            
        self.credentials = (key, secret)
        self.active_cred_label.setText("Active credentials: applied")
        self.active_cred_label.setStyleSheet("color: #2979ff; font-weight: bold;")
        QMessageBox.information(self, 'Success', 'Credentials applied successfully')
    
    def execute_api_call(self):
        """Execute the selected API call"""
        if not self.credentials:
            error_msg = 'Missing credentials. Please set your credentials first.'
            self.results_text.clear()
            self.results_text.setTextColor(QColor("red"))
            self.results_text.append(error_msg)
            return
        
        selected_call = self.call_type_combo.currentText()
        
        # Disable UI elements
        self.execute_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.results_text.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText(f'Executing API call for: {selected_call}')
        
        # Create and start worker thread
        self.worker = ApiWorker(selected_call, self.credentials)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.finished.connect(self.process_results)
        self.worker.error.connect(self.handle_error)
        self.worker.log_output.connect(self.handle_log_output)
        self.worker.start()
        
    def update_progress(self, current_page, total_pages):
        """Update progress bar based on current page vs total pages"""
        if total_pages > 0:
            progress_percent = int((current_page / total_pages) * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_label.setText(f'Processing page {current_page} of {total_pages}')
    
    def handle_log_output(self, log_text):
        """Handle terminal output from the API call"""
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"--- {timestamp} ---\n{log_text}\n\n"
        
        # Append to log text
        self.log_text.append(log_entry)
        
        # Scroll to the bottom
        self.log_text.moveCursor(self.log_text.textCursor().End)
        
    def clear_log(self):
        """Clear the log text area"""
        reply = QMessageBox.question(self, 'Confirm Clear', 
                                    'Are you sure you want to clear the log?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_text.clear()
        
    def process_results(self, all_results):
        """Process the API call results"""
        if all_results:
            # Combine all results into one JSON
            combined_result = json.dumps(all_results, indent=4, ensure_ascii=False)
            
            # Show first part of results in text box
            preview = combined_result[:10000] + "..." if len(combined_result) > 10000 else combined_result
            self.results_text.setTextColor(QColor("black"))
            self.results_text.setText(preview)
            
            # Save combined response to temporary file
            self.output_file = main.get_unique_filename("response")
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(combined_result)
                
            self.progress_label.setText(f'Completed! Results saved to {self.output_file}')
            self.save_btn.setEnabled(True)
        else:
            # Show a clear error message
            self.results_text.clear()
            self.results_text.setTextColor(QColor("red"))
            self.results_text.setFont(QFont('Arial', 14, QFont.Bold))
            self.results_text.append("ERROR: No data returned from API")
            self.results_text.setFont(QFont('Arial', 10))
            self.progress_label.setText('No results found')
            
        self.execute_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        
    def handle_error(self, error_msg):
        """Handle errors from the worker thread"""
        # Display the error in the results text area
        self.results_text.clear()
        self.results_text.setTextColor(QColor("red"))
        self.results_text.setFont(QFont('Arial', 14, QFont.Bold))
        self.results_text.append("ERROR")
        self.results_text.setFont(QFont('Arial', 10))
        self.results_text.append("\nDetails:")
        self.results_text.append(error_msg)
        self.results_text.setTextColor(QColor("black"))
        
        # Also update the progress label
        self.progress_label.setText('Error occurred')
        self.execute_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Still show a small notification
        QMessageBox.critical(self, 'Error', 'An error occurred. See the results panel for details.')
        
    def save_results(self):
        """Save results to a user-selected file"""
        if not self.output_file or not os.path.exists(self.output_file):
            QMessageBox.warning(self, 'No Results', 'No results available to save')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Results', 'omie_results.json', 'JSON Files (*.json)')
            
        if file_path:
            try:
                # If temporary file exists, copy it to the selected location
                with open(self.output_file, 'r', encoding='utf-8') as src_file:
                    content = src_file.read()
                    
                with open(file_path, 'w', encoding='utf-8') as dest_file:
                    dest_file.write(content)
                    
                QMessageBox.information(self, 'Success', f'Results saved to {file_path}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to save file: {str(e)}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    
    # Set application style sheet for modern appearance
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTabWidget::pane {
            border: none;
            background-color: #f5f5f5;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #333333;
            padding: 8px 16px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-weight: bold;
            margin-right: 2px;
            font-size: 10px;
        }
        QTabBar::tab:selected {
            background-color: #2979ff;
            color: white;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QLabel {
            color: #333333;
        }
        QPushButton {
            background-color: #2979ff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #2196f3;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
        QLineEdit, QTextEdit, QComboBox {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px;
            background-color: white;
            min-height: 25px;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 4px;
            text-align: center;
            min-height: 25px;
        }
        QProgressBar::chunk {
            background-color: #2979ff;
            width: 10px;
            margin: 0.5px;
        }
        QToolButton {
            font-weight: bold;
            background-color: transparent;
            padding: 5px;
            border: none;
        }
        QToolButton::menu-indicator {
            image: none;
        }
        QFrame[frameShape="4"] { /* HLine */
            color: #cccccc;
            max-height: 1px;
            margin: 5px 0;
        }
    """)
    
    window = OmieApp()
    window.show()
    sys.exit(app.exec_()) 