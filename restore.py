import sys
import os
import shutil
import zipfile
import json
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# filepath: y:\Code\Windows Backup Creator\restore.py
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QCheckBox, QPushButton, QLabel, 
                             QLineEdit, QFileDialog, QProgressBar, QTextEdit,
                             QGroupBox, QMessageBox)


class RestoreWorker(QThread):
    """Worker thread to perform restore operations without freezing the GUI"""
    progress_update = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    restore_complete = pyqtSignal(bool, str)
    
    def __init__(self, backup_path, is_compressed):
        super().__init__()
        self.backup_path = backup_path
        self.is_compressed = is_compressed
        self.is_cancelled = False
        
    def run(self):
        try:
            current_user = os.path.basename(os.path.expanduser("~"))
            user_profile = os.path.expanduser("~")
            
            # Try to load metadata file
            metadata = self._load_metadata()
            
            if metadata:
                self.progress_update.emit("✓ Metadata file found - using intelligent restore")
                self._restore_with_metadata(metadata, current_user, user_profile)
            else:
                self.progress_update.emit("⚠ No metadata file found - using basic restore")
                self._restore_basic(current_user, user_profile)
                
        except Exception as e:
            self.progress_update.emit(f"Error: {str(e)}")
            self.restore_complete.emit(False, str(e))
    
    def _load_metadata(self):
        """Try to load metadata JSON file from backup"""
        try:
            if self.is_compressed:
                # Look for metadata file in ZIP
                with zipfile.ZipFile(self.backup_path, 'r') as zipf:
                    file_list = zipf.namelist()
                    metadata_files = [f for f in file_list if 'Backup_Metadata' in f and f.endswith('.json')]
                    
                    if metadata_files:
                        metadata_file = metadata_files[0]
                        self.progress_update.emit(f"Reading metadata: {metadata_file}")
                        with zipf.open(metadata_file) as f:
                            return json.load(f)
            else:
                # Look for metadata file in folder
                metadata_file = os.path.join(self.backup_path, "Backup_Metadata.json")
                if os.path.exists(metadata_file):
                    self.progress_update.emit(f"Reading metadata: {metadata_file}")
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            return None
        except Exception as e:
            self.progress_update.emit(f"Warning: Could not read metadata: {str(e)}")
            return None
    
    def _restore_with_metadata(self, metadata, current_user, user_profile):
        """Restore using metadata information"""
        backup_info = metadata.get('backup_info', {})
        folders = metadata.get('folders', [])
        
        original_username = backup_info.get('username', '')
        backup_type = backup_info.get('backup_type', '')
        
        self.progress_update.emit(f"Original backup user: {original_username}")
        self.progress_update.emit(f"Current user: {current_user}")
        self.progress_update.emit(f"Backup type: {backup_type}")
        self.progress_update.emit("-" * 50)
        
        if self.is_compressed:
            self._restore_compressed_with_metadata(folders, original_username, current_user, user_profile)
        else:
            self._restore_folder_with_metadata(folders, original_username, current_user, user_profile)
    
    def _restore_compressed_with_metadata(self, folders, original_username, current_user, user_profile):
        """Restore compressed backup using metadata"""
        self.progress_update.emit(f"Extracting backup from: {self.backup_path}")
        
        with zipfile.ZipFile(self.backup_path, 'r') as zipf:
            file_list = [f for f in zipf.namelist() if not f.endswith('.json') and not f.endswith('.txt')]
            total_files = len(file_list)
            processed = 0
            
            for folder_info in folders:
                if self.is_cancelled:
                    self.restore_complete.emit(False, "Restore cancelled by user")
                    return
                
                folder_name = folder_info['folder_name']
                original_path = folder_info['original_path']
                backup_location = folder_info['backup_location']
                folder_type = folder_info['folder_type']
                
                # Replace old username with current username in original path
                if folder_type == 'user_folder':
                    # Extract the relative path from original_path (e.g., Desktop, Documents)
                    if original_username:
                        # Replace old username path with current user path
                        target_path = original_path.replace(f"Users\\{original_username}", f"Users\\{current_user}")
                        target_path = target_path.replace(f"Users/{original_username}", f"Users/{current_user}")
                    else:
                        # Fallback to user profile + folder name
                        target_path = os.path.join(user_profile, folder_name)
                else:
                    # Custom folders - use original path as-is
                    target_path = original_path
                
                self.progress_update.emit(f"Restoring {folder_name} to {target_path}...")
                
                # Find all files in this backup location
                folder_files = [f for f in file_list if f.startswith(backup_location.replace('\\', '/'))]
                
                for file_name in folder_files:
                    if self.is_cancelled:
                        self.restore_complete.emit(False, "Restore cancelled by user")
                        return
                    
                    try:
                        # Calculate relative path within the folder
                        rel_path = file_name[len(backup_location):].lstrip('/\\').lstrip()
                        
                        # Skip if it's just the folder itself
                        if not rel_path:
                            continue
                        
                        # Target file path
                        target_file = os.path.join(target_path, rel_path)
                        
                        # Create target directory
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        
                        # Extract file
                        with zipf.open(file_name) as source:
                            with open(target_file, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        
                        processed += 1
                        if processed % 10 == 0:
                            progress = int((processed / total_files) * 100)
                            self.progress_value.emit(progress)
                            
                    except Exception as e:
                        self.progress_update.emit(f"Warning: Could not restore {file_name}: {str(e)}")
                
                self.progress_update.emit(f"✓ {folder_name} restored successfully")
        
        self.progress_update.emit("✓ Compressed backup restored successfully!")
        self.restore_complete.emit(True, self.backup_path)
    
    def _restore_folder_with_metadata(self, folders, original_username, current_user, user_profile):
        """Restore folder backup using metadata"""
        self.progress_update.emit(f"Restoring from folder: {self.backup_path}")
        
        total_folders = len(folders)
        
        for idx, folder_info in enumerate(folders):
            if self.is_cancelled:
                self.restore_complete.emit(False, "Restore cancelled by user")
                return
            
            folder_name = folder_info['folder_name']
            original_path = folder_info['original_path']
            backup_location = folder_info['backup_location']
            folder_type = folder_info['folder_type']
            
            # Replace old username with current username in original path
            if folder_type == 'user_folder':
                if original_username:
                    target_path = original_path.replace(f"Users\\{original_username}", f"Users\\{current_user}")
                    target_path = target_path.replace(f"Users/{original_username}", f"Users/{current_user}")
                else:
                    target_path = os.path.join(user_profile, folder_name)
            else:
                # Custom folders - use original path as-is
                target_path = original_path
            
            # Source folder in backup
            source_folder = os.path.join(self.backup_path, backup_location)
            
            self.progress_update.emit(f"Restoring {folder_name} to {target_path}...")
            
            try:
                if os.path.exists(source_folder):
                    # Create target directory
                    os.makedirs(target_path, exist_ok=True)
                    
                    # Copy files recursively
                    for root, dirs, files in os.walk(source_folder):
                        # Calculate relative path
                        rel_path = os.path.relpath(root, source_folder)
                        target_dir = os.path.join(target_path, rel_path) if rel_path != '.' else target_path
                        
                        # Create target directory
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Copy files
                        for file in files:
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(target_dir, file)
                            try:
                                shutil.copy2(src_file, dst_file)
                            except Exception as e:
                                self.progress_update.emit(f"Warning: Could not restore {file}: {str(e)}")
                    
                    self.progress_update.emit(f"✓ {folder_name} restored successfully")
                else:
                    self.progress_update.emit(f"⚠ Skipping {folder_name} - not found in backup")
                    
            except Exception as e:
                self.progress_update.emit(f"✗ Error restoring {folder_name}: {str(e)}")
            
            progress = int(((idx + 1) / total_folders) * 100)
            self.progress_value.emit(progress)
        
        self.progress_update.emit("✓ Folder backup restored successfully!")
        self.restore_complete.emit(True, self.backup_path)
    
    def _restore_basic(self, current_user, user_profile):
        """Fallback basic restore without metadata"""
        if self.is_compressed:
            # Basic restore from ZIP file
            self.progress_update.emit(f"Extracting backup from: {self.backup_path}")
            
            with zipfile.ZipFile(self.backup_path, 'r') as zipf:
                file_list = zipf.namelist()
                total_files = len(file_list)
                
                for idx, file_name in enumerate(file_list):
                    if self.is_cancelled:
                        self.restore_complete.emit(False, "Restore cancelled by user")
                        return
                    
                    # Extract folder name (first part of the path)
                    folder_name = file_name.split('/')[0] if '/' in file_name else file_name.split('\\')[0]
                    
                    # Determine target location based on folder name
                    target_path = os.path.join(user_profile, folder_name)
                    
                    # Extract file
                    try:
                        zipf.extract(file_name, user_profile)
                        
                        if idx % 10 == 0:  # Update every 10 files to avoid spam
                            self.progress_update.emit(f"Restoring: {file_name}")
                        
                        progress = int(((idx + 1) / total_files) * 100)
                        self.progress_value.emit(progress)
                        
                    except Exception as e:
                        self.progress_update.emit(f"Warning: Could not restore {file_name}: {str(e)}")
            
            self.progress_update.emit("✓ Compressed backup restored successfully!")
            self.restore_complete.emit(True, self.backup_path)
            
        else:
            # Basic restore from folder backup
            if not os.path.isdir(self.backup_path):
                self.restore_complete.emit(False, "Invalid backup folder")
                return
            
            self.progress_update.emit(f"Restoring from folder: {self.backup_path}")
            
            # Get list of folders in backup
            backup_folders = [f for f in os.listdir(self.backup_path) 
                            if os.path.isdir(os.path.join(self.backup_path, f))]
            
            # Filter out the programs list file if it exists
            backup_folders = [f for f in backup_folders if f != "Installed_Programs.txt"]
            
            total_folders = len(backup_folders)
            
            for idx, folder_name in enumerate(backup_folders):
                if self.is_cancelled:
                    self.restore_complete.emit(False, "Restore cancelled by user")
                    return
                
                source_folder = os.path.join(self.backup_path, folder_name)
                target_folder = os.path.join(user_profile, folder_name)
                
                self.progress_update.emit(f"Restoring {folder_name}...")
                
                try:
                    # If target folder exists, merge contents
                    if os.path.exists(target_folder):
                        # Copy files recursively, overwriting existing files
                        for root, dirs, files in os.walk(source_folder):
                            # Calculate relative path
                            rel_path = os.path.relpath(root, source_folder)
                            target_dir = os.path.join(target_folder, rel_path) if rel_path != '.' else target_folder
                            
                            # Create target directory if it doesn't exist
                            os.makedirs(target_dir, exist_ok=True)
                            
                            # Copy files
                            for file in files:
                                src_file = os.path.join(root, file)
                                dst_file = os.path.join(target_dir, file)
                                try:
                                    shutil.copy2(src_file, dst_file)
                                except Exception as e:
                                    self.progress_update.emit(f"Warning: Could not restore {file}: {str(e)}")
                    else:
                        # Copy entire folder
                        shutil.copytree(source_folder, target_folder, 
                                      dirs_exist_ok=True,
                                      ignore_dangling_symlinks=True)
                    
                    self.progress_update.emit(f"✓ {folder_name} restored successfully")
                    
                except Exception as e:
                    self.progress_update.emit(f"✗ Error restoring {folder_name}: {str(e)}")
                
                progress = int(((idx + 1) / total_folders) * 100)
                self.progress_value.emit(progress)
            
            self.progress_update.emit("✓ Folder backup restored successfully!")
            self.restore_complete.emit(True, self.backup_path)
    
    def cancel(self):
        self.is_cancelled = True


class RestoreGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows Backup Restorer")
        self.setMinimumSize(800, 850)
        
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Windows Backup Restorer")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Warning message
        warning_label = QLabel("⚠️ Warning: Restoring will overwrite existing files in your user folders!")
        warning_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 10px; background-color: #FFEBEE; border-radius: 5px;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(warning_label)
        
        # Backup location group
        backup_group = QGroupBox("Backup Location")
        backup_layout = QVBoxLayout()
        
        # Compressed ZIP checkbox
        self.is_compressed_checkbox = QCheckBox("Backup is a compressed ZIP file")
        self.is_compressed_checkbox.setChecked(False)
        self.is_compressed_checkbox.setStyleSheet("""
            QCheckBox::indicator:checked {
                background-color: #FF9800;
            }
            QCheckBox::indicator:unchecked {
                background-color: #FFFFFF;
            }
        """)
        self.is_compressed_checkbox.stateChanged.connect(self.on_compressed_changed)
        backup_layout.addWidget(self.is_compressed_checkbox)
        
        # Browse layout
        browse_layout = QHBoxLayout()
        
        self.backup_input = QLineEdit()
        self.backup_input.setPlaceholderText("Select backup location...")
        self.backup_input.setReadOnly(True)
        browse_layout.addWidget(self.backup_input)
        
        self.browse_btn = QPushButton("Browse for Folder...")
        self.browse_btn.clicked.connect(self.browse_backup)
        browse_layout.addWidget(self.browse_btn)
        
        backup_layout.addLayout(browse_layout)
        backup_group.setLayout(backup_layout)
        main_layout.addWidget(backup_group)
        
        # Info section
        info_group = QGroupBox("Backup Information")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel("No backup selected")
        self.info_label.setStyleSheet("padding: 1px;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Progress section
        progress_label = QLabel("Restore Progress:")
        main_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #FF9800;
                width: 10px;
                margin: 0.5px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Log area
        log_label = QLabel("Restore Log:")
        main_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        main_layout.addWidget(self.log_text)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("Start Restore")
        self.restore_btn.setMinimumHeight(40)
        self.restore_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; }")
        self.restore_btn.clicked.connect(self.start_restore)
        self.restore_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_restore)
        
        action_layout.addWidget(self.restore_btn)
        action_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(action_layout)
        
        # Footer
        main_layout.addStretch()
        footer_label = QLabel('Created by Glitch - <a href="https://github.com/glitch-codes">https://github.com/glitch-codes</a>')
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #666; font-size: 10pt; padding: 10px;")
        footer_label.setOpenExternalLinks(True)
        main_layout.addWidget(footer_label)
    
    def on_compressed_changed(self, state):
        """Update browse button text based on checkbox state"""
        if state == Qt.CheckState.Checked.value:
            self.browse_btn.setText("Browse for ZIP File...")
        else:
            self.browse_btn.setText("Browse for Folder...")
        
        # Clear selection when changing mode
        self.backup_input.clear()
        self.info_label.setText("No backup selected")
        self.restore_btn.setEnabled(False)
    
    def browse_backup(self):
        """Browse for backup location (folder or ZIP file)"""
        if self.is_compressed_checkbox.isChecked():
            # Browse for ZIP file
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Backup ZIP File", "", "ZIP Files (*.zip);;All Files (*)"
            )
            if file_path:
                self.backup_input.setText(file_path)
                self.show_backup_info(file_path, True)
                self.restore_btn.setEnabled(True)
        else:
            # Browse for folder
            folder_path = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
            if folder_path:
                self.backup_input.setText(folder_path)
                self.show_backup_info(folder_path, False)
                self.restore_btn.setEnabled(True)
    
    def show_backup_info(self, path, is_compressed):
        """Display information about the selected backup"""
        try:
            info_text = f"<b>Backup Location:</b> {path}<br>"
            info_text += f"<b>Type:</b> {'Compressed ZIP' if is_compressed else 'Folder'}<br>"
            
            # Try to load metadata
            metadata = self._try_load_metadata_preview(path, is_compressed)
            if metadata:
                backup_info = metadata.get('backup_info', {})
                info_text += f"<b>Backup Date:</b> {backup_info.get('datetime', 'Unknown')}<br>"
                info_text += f"<b>Original User:</b> {backup_info.get('username', 'Unknown')}<br>"
                info_text += f"<b>Has Metadata:</b> Yes ✓<br><br>"
                
                folders = metadata.get('folders', [])
                user_folders = [f['folder_name'] for f in folders if f['folder_type'] == 'user_folder']
                custom_folders = [f['folder_name'] for f in folders if f['folder_type'] == 'custom_folder']
                
                if user_folders:
                    info_text += f"<b>User Folders:</b> {', '.join(user_folders)}<br>"
                if custom_folders:
                    info_text += f"<b>Custom Folders:</b> {', '.join(custom_folders)}<br>"
            else:
                info_text += f"<b>Has Metadata:</b> No (will use basic restore)<br><br>"
            
            if is_compressed:
                # Get info from ZIP
                with zipfile.ZipFile(path, 'r') as zipf:
                    file_list = zipf.namelist()
                    folders = set()
                    for file_name in file_list:
                        folder = file_name.split('/')[0] if '/' in file_name else file_name.split('\\')[0]
                        if folder:
                            folders.add(folder)
                    
                    info_text += f"<b>Total Files:</b> {len(file_list)}<br>"
                    info_text += f"<b>Folders to Restore:</b> {', '.join(sorted(folders))}"
            else:
                # Get info from folder
                folders = [f for f in os.listdir(path) 
                          if os.path.isdir(os.path.join(path, f))]
                folders = [f for f in folders if f != "Installed_Programs.txt"]
                
                total_files = 0
                for folder in folders:
                    folder_path = os.path.join(path, folder)
                    total_files += sum(len(files) for _, _, files in os.walk(folder_path))
                
                info_text += f"<b>Total Files:</b> ~{total_files}<br>"
                info_text += f"<b>Folders to Restore:</b> {', '.join(sorted(folders))}"
            
            self.info_label.setText(info_text)
            
        except Exception as e:
            self.info_label.setText(f"<span style='color: red;'>Error reading backup: {str(e)}</span>")
            self.restore_btn.setEnabled(False)
    
    def _try_load_metadata_preview(self, path, is_compressed):
        """Try to load metadata for preview without starting restore"""
        try:
            if is_compressed:
                with zipfile.ZipFile(path, 'r') as zipf:
                    file_list = zipf.namelist()
                    metadata_files = [f for f in file_list if 'Backup_Metadata' in f and f.endswith('.json')]
                    if metadata_files:
                        with zipf.open(metadata_files[0]) as f:
                            return json.load(f)
            else:
                metadata_file = os.path.join(path, "Backup_Metadata.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except:
            pass
        return None
    
    def log_message(self, message):
        """Add message to log"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def start_restore(self):
        """Start the restore process"""
        backup_path = self.backup_input.text().strip()
        
        if not backup_path:
            QMessageBox.warning(self, "No Backup Selected", 
                              "Please select a backup location first.")
            return
        
        # Confirm restore operation
        reply = QMessageBox.warning(
            self, "Confirm Restore",
            "⚠️ WARNING ⚠️\n\n"
            "This will restore files from the backup to your user folders.\n"
            "Existing files with the same names will be OVERWRITTEN!\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Disable UI during restore
        self.restore_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.is_compressed_checkbox.setEnabled(False)
        
        # Clear log and reset progress
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        self.log_message("Starting restore process...")
        self.log_message(f"Backup location: {backup_path}")
        self.log_message(f"Type: {'Compressed ZIP' if self.is_compressed_checkbox.isChecked() else 'Folder'}")
        self.log_message("-" * 50)
        
        # Start restore worker thread
        self.worker = RestoreWorker(
            backup_path,
            self.is_compressed_checkbox.isChecked()
        )
        self.worker.progress_update.connect(self.log_message)
        self.worker.progress_value.connect(self.progress_bar.setValue)
        self.worker.restore_complete.connect(self.restore_finished)
        self.worker.start()
    
    def cancel_restore(self):
        """Cancel the restore operation"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Restore",
                "Are you sure you want to cancel the restore?\n\n"
                "Note: Already restored files will not be removed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message("Cancelling restore...")
                self.worker.cancel()
    
    def restore_finished(self, success, result):
        """Handle restore completion"""
        # Re-enable UI
        self.restore_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.is_compressed_checkbox.setEnabled(True)
        
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            self.log_message("-" * 50)
            self.log_message("✓ Restore completed successfully!")
            QMessageBox.information(
                self, "Restore Complete",
                "Restore completed successfully!\n\n"
                "Your files have been restored to their original locations."
            )
        else:
            self.log_message("-" * 50)
            self.log_message(f"✗ Restore failed: {result}")
            QMessageBox.critical(
                self, "Restore Failed",
                f"Restore failed with error:\n\n{result}"
            )


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = RestoreGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()