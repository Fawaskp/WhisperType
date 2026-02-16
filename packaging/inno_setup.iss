; WhisperType — Inno Setup installer script
; Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; Usage:  iscc packaging\inno_setup.iss
; Input:  dist\WhisperType\  (PyInstaller output)
; Output: dist\WhisperType-Setup.exe

[Setup]
AppName=WhisperType
AppVersion=1.0.0
AppPublisher=WhisperType
DefaultDirName={autopf}\WhisperType
DefaultGroupName=WhisperType
OutputDir=..\dist
OutputBaseFilename=WhisperType-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=
UninstallDisplayIcon={app}\WhisperType.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Files]
Source: "..\dist\WhisperType\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\WhisperType"; Filename: "{app}\WhisperType.exe"
Name: "{group}\Uninstall WhisperType"; Filename: "{uninstallexe}"
Name: "{autodesktop}\WhisperType"; Filename: "{app}\WhisperType.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\WhisperType.exe"; Description: "Launch WhisperType"; Flags: nowait postinstall skipifsilent
