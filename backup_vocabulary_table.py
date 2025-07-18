#!/usr/bin/env python3
"""
Backup vocabulary_new table from enspiring database to local Downloads folder
Uses mysqldump command with database connection info from helping_page.py
"""

import os
import subprocess
import datetime
from pathlib import Path

# Import database connection variables from helping_page.py
from helping_page import DB_ENSPIRING_HOST, DB_HOST_LOCAL, DB_USER_NEW, DB_PASSWORD_NEW, DB_PORT, DB_NAME_GHOST, which_ubuntu

def backup_vocabulary_table():
    """
    Backup vocabulary_new table using mysqldump command
    """
    try:
        # Determine database host based on environment (same logic as get_engine)
        db_host = DB_HOST_LOCAL if which_ubuntu == 'AWS' else DB_ENSPIRING_HOST
        
        print(f"🔍 Creating mysqldump backup from {db_host}...")
        
        # Create backup file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"vocabulary_new_backup_{timestamp}.sql"
        local_backup_path = Path.home() / "Downloads" / backup_filename
        
        # Create mysqldump command
        mysqldump_cmd = [
            "mysqldump",
            f"-h{db_host}",
            f"-P{DB_PORT}",
            f"-u{DB_USER_NEW}",
            f"-p{DB_PASSWORD_NEW}",
            "--single-transaction",
            "--no-tablespaces",
            DB_NAME_GHOST,
            "vocabulary_new"
        ]
        
        print(f"Command: mysqldump -h{db_host} -P{DB_PORT} -u{DB_USER_NEW} -p[password] --single-transaction --no-tablespaces {DB_NAME_GHOST} vocabulary_new")
        
        # Execute mysqldump and save to local file
        with open(local_backup_path, 'w', encoding='utf-8') as backup_file:
            result = subprocess.run(
                mysqldump_cmd,
                stdout=backup_file,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode == 0:
            print(f"✅ Backup successful!")
            print(f"📁 File saved to: {local_backup_path}")
            print(f"📊 File size: {local_backup_path.stat().st_size / 1024:.2f} KB")
            return str(local_backup_path)
        else:
            print(f"❌ Backup failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error during backup: {e}")
        return None

def main():
    """
    Main function to run the backup
    """
    print("🗄️  vocabulary_new Table Backup Tool")
    print("=" * 50)
    
    result = backup_vocabulary_table()
    
    if result:
        print(f"\n🎉 Backup completed successfully!")
        print(f"📁 Location: {result}")
        
        # Ask if user wants to open the Downloads folder
        open_folder = input("\nOpen Downloads folder? (y/n): ").strip().lower()
        if open_folder == 'y':
            subprocess.run(["open", str(Path.home() / "Downloads")])

if __name__ == "__main__":
    main()
