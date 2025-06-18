# setup_fixed.py
"""
Fixed PyInstaller setup script for Employee Sleep Tracker
This script creates a standalone executable for the application
"""

import PyInstaller.__main__
import os
import sys

def create_exe():
    """Create executable using PyInstaller"""
    
    # PyInstaller arguments - FIXED VERSION
    args = [
        'main.py',  # Entry point
        '--name=EmployeeSleepTracker',  # Executable name
        '--onefile',  # Create single executable file
        '--windowed',  # Remove console window (GUI app)
        # '--icon=icon.ico',  # Application icon (commented out - not needed)
        '--add-data=config;config',  # Include config directory
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui', 
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=pyodbc',
        '--hidden-import=win32gui',
        '--hidden-import=win32con',
        '--hidden-import=win32api',
        '--hidden-import=win32ts',
        '--hidden-import=wmi',
        '--hidden-import=pythoncom',
        '--collect-all=pywin32',
        '--collect-all=wmi',
        '--noconsole',  # No console window
        '--clean',  # Clean cache
        '--distpath=dist',  # Output directory
        '--workpath=build',  # Build directory
        '--specpath=.',  # Spec file location
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    print("Creating executable for Employee Sleep Tracker...")
    print("This may take a few minutes...")
    try:
        create_exe()
        print("\n" + "="*50)
        print("✅ SUCCESS! Executable created successfully!")
        print("📁 Location: dist/EmployeeSleepTracker.exe")
        print("="*50)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTry running the manual command instead:")
        print("pyinstaller --onefile --windowed --name=EmployeeSleepTracker main.py")
