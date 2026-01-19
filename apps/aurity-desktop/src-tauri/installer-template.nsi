# Custom NSIS template for Aurity Desktop with Python installation
# Based on Tauri's default template with Python integration

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

# Variables
Var PythonFound
Var PythonVersion
Var PythonPath

# Python installation section (runs BEFORE main app)
Section "Install Python 3.14 Runtime" SecPython
  # Check if Python 3.14+ already exists (single optimized call)
  DetailPrint "Checking for Python 3.14+..."

  # Combined check: version detection in one call
  nsExec::ExecToStack 'python -c "import sys; v=sys.version_info; print(f\"$${v.major}.$${v.minor}\")"'
  Pop $0  # Return code
  Pop $PythonVersion

  ${If} $0 == 0
    # Python found, validate version
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

    # Extract files to temp directory (consolidated)
    SetOutPath "$TEMP"
    File "resources\python-installer\python-3.14.0-amd64.exe"
    File "resources\python-installer\fi-monitor-requirements.txt"

    # Run Python installer with timeout (max 5 minutes)
    # /quiet - Silent install
    # InstallAllUsers=0 - Per-user install (no admin required)
    # PrependPath=1 - Add to PATH
    # Include_pip=1 - Install pip
    # Include_tcltk=0 - Skip Tk/Tcl (not needed)
    # Include_test=0 - Skip test suite
    nsExec::ExecToStack '"$TEMP\python-3.14.0-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=0 Include_test=0'
    Pop $0  # Return code
    Pop $1  # Output (ignored)

    ${If} $0 == 0
      DetailPrint "✅ Python 3.14 installed successfully"

      # Set Python path dynamically
      StrCpy $PythonPath "$LOCALAPPDATA\Programs\Python\Python314\python.exe"

      # Install fi-monitor dependencies with retry logic
      # --timeout=60: Increase from default 15s for corporate networks
      # --retries=3: pip native retry with exponential backoff
      # --prefer-binary: Use pre-compiled wheels (faster, no build tools needed)
      DetailPrint "Installing fi-monitor dependencies..."
      nsExec::ExecToLog '"$PythonPath" -m pip install --quiet --timeout=60 --retries=3 --prefer-binary --no-warn-script-location -r "$TEMP\fi-monitor-requirements.txt"'
      Pop $0

      ${If} $0 != 0
        # Retry once on failure (network issues, etc.)
        DetailPrint "⚠️ Retry: Installing dependencies (attempt 2)..."
        Sleep 2000  # Wait 2 seconds before retry
        nsExec::ExecToLog '"$PythonPath" -m pip install --quiet --timeout=60 --retries=3 --prefer-binary --no-warn-script-location -r "$TEMP\fi-monitor-requirements.txt"'
        Pop $0
      ${EndIf}

      ${If} $0 == 0
        DetailPrint "✅ Dependencies installed"
      ${Else}
        DetailPrint "⚠️ Warning: Failed to install dependencies after 2 attempts (exit code $0)"
        DetailPrint "   FI Monitor may require manual dependency installation"
      ${EndIf}

      # Cleanup temp files
      Delete "$TEMP\python-3.14.0-amd64.exe"
      Delete "$TEMP\fi-monitor-requirements.txt"
    ${Else}
      DetailPrint "❌ Python installation failed (exit code $0)"

      # Show error dialog only in interactive mode (skip if /S flag used)
      IfSilent skip_python_error_dialog
        MessageBox MB_ICONEXCLAMATION|MB_OK "Python installation failed with exit code $0.$\nFI Monitor may not work properly.$\n$\nYou can install Python 3.14+ manually from python.org"
      skip_python_error_dialog:

      # Cleanup on failure
      Delete "$TEMP\python-3.14.0-amd64.exe"
      Delete "$TEMP\fi-monitor-requirements.txt"
    ${EndIf}
  ${Else}
    DetailPrint "Skipping Python installation (already present)"
  ${EndIf}
SectionEnd

# Main application section (standard Tauri section follows here)
# Tauri will inject its default sections below this line
