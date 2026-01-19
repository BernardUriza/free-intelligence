# Custom NSIS template for Aurity Desktop with Python installation
# Based on Tauri's default template with Python integration

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

# Variables
Var PythonFound
Var PythonVersion
Var InstallPython

# Python installation section (runs BEFORE main app)
Section "Install Python 3.14 Runtime" SecPython
  # Check if Python 3.14+ already exists
  DetailPrint "Checking for Python 3.14+..."

  nsExec::ExecToStack 'python --version'
  Pop $0  # Return code
  Pop $1  # Output

  ${If} $0 == 0
    # Python found, extract version
    nsExec::ExecToStack 'python -c "import sys; v=sys.version_info; print(f\"$${v.major}.$${v.minor}\")"'
    Pop $0
    Pop $PythonVersion

    ${VersionCompare} "$PythonVersion" "3.14" $2
    ${If} $2 == 0
      # Exact match
      StrCpy $PythonFound "true"
      DetailPrint "✅ Python $PythonVersion found (compatible)"
    ${ElseIf} $2 == 1
      # Newer version
      StrCpy $PythonFound "true"
      DetailPrint "✅ Python $PythonVersion found (newer than 3.14)"
    ${Else}
      # Older version
      StrCpy $PythonFound "false"
      DetailPrint "⚠️ Python $PythonVersion found (too old)"
    ${EndIf}
  ${Else}
    StrCpy $PythonFound "false"
    DetailPrint "⚠️ Python not found in PATH"
  ${EndIf}

  ${If} $PythonFound == "false"
    DetailPrint "Installing Python 3.14 Full..."

    # Extract Python installer from resources
    SetOutPath "$TEMP"
    File "resources\python-installer\python-3.14.0-amd64.exe"

    # Run Python installer silently with options:
    # /quiet - Silent install
    # InstallAllUsers=0 - Per-user install (no admin required)
    # PrependPath=1 - Add to PATH
    # Include_pip=1 - Install pip
    # Include_tcltk=0 - Skip Tk/Tcl (not needed)
    # Include_test=0 - Skip test suite
    ExecWait '"$TEMP\python-3.14.0-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=0 Include_test=0' $0

    ${If} $0 == 0
      DetailPrint "✅ Python 3.14 installed successfully"

      # Install fi-monitor dependencies
      DetailPrint "Installing fi-monitor dependencies..."
      SetOutPath "$TEMP"
      File "resources\python-installer\fi-monitor-requirements.txt"

      # Use python from %LOCALAPPDATA%\Programs\Python\Python314
      nsExec::ExecToLog '"$LOCALAPPDATA\Programs\Python\Python314\python.exe" -m pip install --quiet -r "$TEMP\fi-monitor-requirements.txt"'
      Pop $0

      ${If} $0 == 0
        DetailPrint "✅ Dependencies installed"
      ${Else}
        DetailPrint "⚠️ Warning: Failed to install dependencies (code $0)"
      ${EndIf}

      # Cleanup
      Delete "$TEMP\python-3.14.0-amd64.exe"
      Delete "$TEMP\fi-monitor-requirements.txt"
    ${Else}
      DetailPrint "❌ Python installation failed (code $0)"
      MessageBox MB_ICONEXCLAMATION|MB_OK "Python installation failed. FI Monitor may not work properly."
    ${EndIf}
  ${Else}
    DetailPrint "Skipping Python installation (already present)"
  ${EndIf}
SectionEnd

# Main application section (standard Tauri section follows here)
# Tauri will inject its default sections below this line
