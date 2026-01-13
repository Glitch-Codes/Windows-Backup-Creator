# Windows Backup Creator

A comprehensive PyQt6-based GUI application for backing up and restoring Windows user folders with advanced features including metadata tracking, custom folder support, and intelligent restoration capabilities.

## Features

### Backup Features
- **Comprehensive Folder Detection**: Automatically finds all user profile folders including:
  - Desktop, Documents, Downloads, Pictures, Videos, Music (default selected)
  - AppData, Contacts, Favorites, Links, Saved Games, Searches (optional)
- **Custom Folder Support**: Add any custom folders outside the user profile to your backup
- **Installed Programs List**: Export a list of all installed programs from Windows Registry
- **Selective Backup**: Choose which folders to backup with checkboxes
- **Smart Downloads Handling**: Option to limit Downloads folder files to 2GB (skips larger files)
- **Flexible Destination**: Browse and select any destination folder
- **ZIP Compression**: Optional compression into a single ZIP file
- **Metadata Generation**: Automatically creates backup metadata for intelligent restoration
- **Embedded Restorer**: Folder backups include a portable restore application
- **Configuration Profiles**: Save and load different backup configurations
- **Progress Tracking**: Real-time progress bar and detailed logging
- **Threaded Operations**: Non-blocking backup process that doesn't freeze the UI
- **Timestamped Backups**: Each backup is automatically timestamped
- **Fun Accent Colours**: Switch between visual accent colours, I like orange but you may not

### Restore Features
- **Intelligent Restoration**: Uses backup metadata for accurate folder restoration
- **Username Migration**: Automatically handles restoring to different user accounts
- **Folder Mapping**: Maps original folder paths to current user profile folders
- **Selective Restore**: Choose which folders to restore from the backup
- **Progress Tracking**: Real-time progress updates during restoration
- **Compressed & Folder Support**: Restore from both ZIP files and folder backups
- **Basic Restore Mode**: Falls back to basic restoration if metadata is unavailable

## Installation

### Running from Binary
1. Download the latest release from the releases section or by this link: 
   https://github.com/Glitch-Codes/Windows-Backup-Creator/releases/tag/v1.0
2. Run WindowsBackupCreator-v#.#.exe 
     - If prompted with Windows Smart Screen, click "More Info" and then click "Run Anyways"

### Running from Source
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Building Executables
Build standalone executables using PyInstaller:
```bash
# Build Backup Creator
pyinstaller --onefile --windowed --name "Windows Backup Creator" backup.py

# Build Restorer
pyinstaller --onefile --windowed --name "Windows Backup Restorer" restore.py
```

The executables will be created in the `dist/` folder.

## Usage

### Backup Application
Run the backup application:
```bash
python backup.py
```

#### Steps:
1. Select which user profile folders you want to backup (common folders are selected by default)
2. Optionally add custom folders using "Add Custom Folder" button
   - You can use the "Scan for Non-Windows Folders" to reveal possibly wanted files on the root of your C: drive
3. Optionally enable "Get list of installed programs" to export installed software list
4. Optionally enable "Limit Downloads folder files to 2GB" to skip large files
5. Click "Browse..." to select your backup destination
6. Optionally check "Compress backup into a single ZIP file" for compressed backup
   - Enabling compressed ZIP does not save the restorer program, you will need to download it seperately
7. Click "Start Backup" to begin
8. Monitor progress in the log window
9. Optionally save your configuration with File → Save Configuration
   - Not needed unless you want to run this often
10. Open the backup location when complete

### Restore Application
Run the restore application:
```bash
python restore.py
```

#### Steps:
1. Browse and select your backup (ZIP file or folder)
2. Review the detected folders in the log
3. Click "Start Restore" to restore all files
4. Monitor progress in the log window

## Requirements

- Windows OS
- Python 3.8+
- PyQt6

## Project Structure

- `backup.py` - Main backup application with GUI
- `restore.py` - Standalone restore application
- `create_embedded.py` - Script to embed the restore executable for folder backups
- `embedded_restore.py` - Base64-encoded restore executable (generated)
- `requirements.txt` - Python package dependencies
- `Windows Backup Creator.spec` - PyInstaller specification for backup app
- `Windows Backup Restorer.spec` - PyInstaller specification for restore app

## Backup Structure

### Compressed Backup (ZIP)
```
Backup_2026-01-12_14-30-00.zip
├── [Username]/
│   ├── Desktop/
│   ├── Documents/
│   ├── Downloads/
│   └── ...
├── [CustomFolder1]/
├── [CustomFolder2]/
└── Backup_Metadata_2026-01-12_14-30-00.json
Installed_Programs_2026-01-12_14-30-00.txt (if enabled)
```

### Folder Backup
```
Backup_2026-01-12_14-30-00/
├── [Username]/
│   ├── Desktop/
│   ├── Documents/
│   ├── Downloads/
│   └── ...
├── [CustomFolder1]/
├── [CustomFolder2]/
├── Backup_Metadata.json
├── Installed_Programs.txt (if enabled)
└── Windows Backup Restorer.exe
```

## Metadata File

The backup metadata JSON file contains:
- Backup timestamp and creation date
- Original username
- Backup type (compressed/folder)
- Folder mappings (original paths, folder types, backup locations)
- Installed programs list (if enabled)
- Download limit settings
- Restore instructions

This metadata enables intelligent restoration across different user accounts and systems.

## Notes

- User profile folders are organized under the username folder in backups
- Custom folders are stored at the root level of the backup
- Folders that don't exist are automatically disabled in the UI
- Backups are named with timestamps: `Backup_YYYY-MM-DD_HH-MM-SS`
- ZIP files are created with compression for space efficiency
- You can cancel backups in progress
- Folder backups include a portable restore executable
- Configurations are saved in the same directory as the application
- The restore application can handle username differences automatically
