import base64
import os

# Read the executable
exe_path = r"y:\Code\Windows Backup Creator\dist\Windows Backup Restorer.exe"
with open(exe_path, 'rb') as f:
    exe_data = f.read()

# Encode as base64
encoded = base64.b64encode(exe_data).decode('ascii')

# Split into chunks of 76 characters (standard base64 line length)
chunk_size = 76
chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]

# Write to Python file
output_path = r"y:\Code\Windows Backup Creator\embedded_restore.py"
with open(output_path, 'w') as f:
    f.write('"""Embedded Windows Backup Restorer executable"""\n')
    f.write('import base64\n')
    f.write('import os\n')
    f.write('import tempfile\n\n')
    f.write('# Base64 encoded executable data\n')
    f.write('RESTORE_EXE_DATA = (\n')
    
    for chunk in chunks:
        f.write(f'    "{chunk}"\n')
    
    f.write(')\n\n')
    f.write('def extract_restore_exe():\n')
    f.write('    """Extract the restore executable to a temporary file and return the path"""\n')
    f.write('    exe_data = base64.b64decode(RESTORE_EXE_DATA)\n')
    f.write('    temp_dir = tempfile.gettempdir()\n')
    f.write('    exe_path = os.path.join(temp_dir, "Windows_Backup_Restorer_temp.exe")\n')
    f.write('    with open(exe_path, "wb") as f:\n')
    f.write('        f.write(exe_data)\n')
    f.write('    return exe_path\n\n')
    f.write('def get_restore_exe_size():\n')
    f.write('    """Return the size of the embedded executable in bytes"""\n')
    f.write('    return len(base64.b64decode(RESTORE_EXE_DATA))\n')

print(f"Embedded restore executable created successfully!")
print(f"Original size: {len(exe_data):,} bytes")
print(f"Encoded size: {len(encoded):,} characters")
print(f"Output file: {output_path}")
