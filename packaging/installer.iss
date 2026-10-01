; Inno Setup script: per-user install, no admin rights needed.
; Built in CI: iscc /DAppVersion=0.1.0 packaging\installer.iss
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{8C1B7E52-3D5A-4C1E-9B7A-5F2D4A6C9E11}
AppName=Store Listing Kit
AppVersion={#AppVersion}
AppPublisher=Store Listing Kit
DefaultDirName={localappdata}\Programs\StoreListingKit
DefaultGroupName=Store Listing Kit
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=StoreListingKit-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\StoreListingKit.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\StoreListingKit\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; Editor bridges, also available for manual copying.
Source: "..\src\storelistingkit\bridges\*"; DestDir: "{app}\EditorBridges"; Flags: recursesubdirs ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\StoreListingKit"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

[Icons]
Name: "{group}\Store Listing Kit"; Filename: "{app}\StoreListingKit.exe"
Name: "{group}\Editor bridges folder"; Filename: "{app}\EditorBridges"
Name: "{group}\Uninstall Store Listing Kit"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Store Listing Kit"; Filename: "{app}\StoreListingKit.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\StoreListingKit.exe"; Description: "Launch Store Listing Kit"; Flags: nowait postinstall skipifsilent
