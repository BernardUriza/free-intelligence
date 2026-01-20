# Custom NSIS template for Aurity Desktop with Python installation
# Based on Tauri's default template with Python integration

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

# Windows API Constants
# Note: HWND_BROADCAST is provided by Tauri's default template
!ifndef HWND_BROADCAST
  !define HWND_BROADCAST 0xFFFF
!endif
!define WM_SETTINGCHANGE 0x1A

# Variables
Var PythonFound
Var PythonVersion
Var PythonPath

# ============================================
# UTILITY FUNCTIONS
# ============================================

# Validates that Python is accessible and broadcasts PATH changes if needed
# Input (stack): Python executable path
# Output (stack): Return code (0=success, 1=failed)
Function ValidatePythonPath
  Pop $R0  # Python path

  DetailPrint "Verifying Python at: $R0"
  nsExec::ExecToStack '"$R0" --version'
  Pop $R1  # Return code
  Pop $R2  # Output (ignored)

  ${If} $R1 != 0
    DetailPrint "⚠️ PATH not updated, broadcasting environment change..."
    # Broadcast WM_SETTINGCHANGE to refresh PATH without reboot
    SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
    Sleep 1000  # Wait for apps to process broadcast

    # Retry verification
    nsExec::ExecToStack '"$R0" --version'
    Pop $R1
    Pop $R2
  ${EndIf}

  Push $R1  # Return status
FunctionEnd

# Installs pip dependencies with retry logic and logging
# Input (stack, in order): Python path, requirements file path, log file path
# Output (stack): Return code (0=success, non-zero=failed)
Function InstallPipDependencies
  Pop $R2  # Log path
  Pop $R1  # Requirements path
  Pop $R0  # Python path

  DetailPrint "Installing dependencies from: $R1"
  DetailPrint "Log file: $R2"

  # First attempt with full pip options
  # --log: Save detailed log for debugging
  # --timeout=60: Increase from default 15s for corporate networks
  # --retries=3: pip native retry with exponential backoff
  # --prefer-binary: Use pre-compiled wheels (faster, no build tools needed)
  nsExec::ExecToLog '"$R0" -m pip install --log "$R2" --quiet --timeout=60 --retries=3 --prefer-binary --no-warn-script-location -r "$R1"'
  Pop $R3  # Return code

  ${If} $R3 != 0
    DetailPrint "⚠️ First attempt failed (exit code $R3)"
    DetailPrint "⚠️ Retry: Installing dependencies (attempt 2)..."
    Sleep 2000  # Wait before retry

    # Second attempt
    nsExec::ExecToLog '"$R0" -m pip install --log "$R2" --quiet --timeout=60 --retries=3 --prefer-binary --no-warn-script-location -r "$R1"'
    Pop $R3

    ${If} $R3 != 0
      DetailPrint "❌ Failed after 2 attempts (exit code $R3)"
      DetailPrint "   Log saved at: $R2"
      # Keep log file for debugging (don't delete)
    ${Else}
      DetailPrint "✅ Dependencies installed on retry"
      Delete "$R2"  # Cleanup log on success
    ${EndIf}
  ${Else}
    DetailPrint "✅ Dependencies installed"
    Delete "$R2"  # Cleanup log on success
  ${EndIf}

  Push $R3  # Return status
FunctionEnd

# ============================================
# MAIN INSTALLATION SECTION
# ============================================

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

    # Run Python installer
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

      # Validate PATH configuration
      Push "$PythonPath"
      Call ValidatePythonPath
      Pop $0  # Get validation result (0=success)

      ${If} $0 == 0
        DetailPrint "✅ Python PATH verified"
      ${Else}
        DetailPrint "⚠️ Warning: Python PATH verification failed, continuing anyway..."
      ${EndIf}

      # Install fi-monitor dependencies using utility function
      Push "$PythonPath"
      Push "$TEMP\fi-monitor-requirements.txt"
      Push "$TEMP\aurity-pip-install.log"
      Call InstallPipDependencies
      Pop $0  # Get result (0=success)

      ${If} $0 == 0
        DetailPrint "✅ All dependencies installed successfully"
      ${Else}
        DetailPrint "⚠️ Warning: Failed to install dependencies (exit code $0)"
        DetailPrint "   FI Monitor may require manual dependency installation"
        DetailPrint "   Check log at: $TEMP\aurity-pip-install.log"
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
