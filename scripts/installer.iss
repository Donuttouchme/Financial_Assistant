; Financial Assistant Inno Setup script
; Run via:   ISCC.exe /DMyAppVersion=1.0 scripts/installer.iss

#define MyAppName "Financial Assistant"
#define MyAppPublisher "Donuttouchme"
#define MyAppURL "https://github.com/Donuttouchme/Financial_Assistant"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

[Setup]
; Fixed GUID — changing this would make a new release look like a separate app.
AppId={{8F4C9D2A-1B5E-4A6F-9C3D-7E8B2A1D5F0C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\FinancialAssistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=..\dist
OutputBaseFilename=Financial-Assistant-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\RUN.bat
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\portable-staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\RUN.bat"; IconFilename: "{app}\frontend\dist\favicon.svg"; WorkingDir: "{app}"; Comment: "Open Financial Assistant in your browser"
Name: "{group}\Stop {#MyAppName}"; Filename: "{app}\STOP.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\RUN.bat"; IconFilename: "{app}\frontend\dist\favicon.svg"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\RUN.bat"; Description: "Launch {#MyAppName} now"; Flags: postinstall nowait shellexec skipifsilent

[UninstallRun]
; Best-effort: stop the running backend before files get removed.
Filename: "{app}\STOP.bat"; RunOnceId: "StopFinancialAssistant"; Flags: skipifdoesntexist

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Inno Setup will automatically run the previous install's uninstaller
  // before extracting the new files (because of the matching AppId GUID).
  // The previous uninstaller's [UninstallRun] section calls STOP.bat,
  // which terminates the running backend if any. No additional logic needed
  // here.
end;
