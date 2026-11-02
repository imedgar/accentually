; Inno Setup script. Build with: iscc /DAppVersion=1.0.0 installer\accentually.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0E8B6E-5D0B-4B6A-9E55-ACCE17A11F01}
AppName=Accentually
AppVersion={#AppVersion}
AppPublisher=imedgar
AppPublisherURL=https://github.com/imedgar/accentually
DefaultDirName={autopf}\Accentually
DefaultGroupName=Accentually
; Per-user install: no admin prompt, and the in-app updater can replace files silently.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Accentually-Setup
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\Accentually.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=no
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "startup"; Description: "Start Accentually when I sign in to Windows"; GroupDescription: "Options:"

[Files]
Source: "..\dist\Accentually\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Accentually"; Filename: "{app}\Accentually.exe"
Name: "{group}\Uninstall Accentually"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Accentually"; ValueData: """{app}\Accentually.exe"""; Flags: uninsdeletevalue; Tasks: startup
; Entry written by pre-installer versions pointed at a source folder that may be gone.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "QuickAccent"; ValueType: none; Flags: deletevalue

[Run]
; Interactive installs offer a "launch" checkbox; silent installs (updates) always relaunch.
Filename: "{app}\Accentually.exe"; Description: "Launch Accentually"; Flags: nowait postinstall skipifsilent
Filename: "{app}\Accentually.exe"; Flags: nowait; Check: WizardSilent

[Code]
const
  AppMutex = 'Local\QuickAccent_SingleInstance_Mutex';

// During an in-app update the running app exits just after starting this installer, so
// wait briefly for it. If it is still running (manual install over a live copy), stop it:
// it is a windowless tray app that Windows' Restart Manager cannot close.
function InitializeSetup(): Boolean;
var
  I, ResultCode: Integer;
begin
  for I := 1 to 15 do
  begin
    if not CheckForMutexes(AppMutex) then
      Break;
    Sleep(200);
  end;
  if CheckForMutexes(AppMutex) then
  begin
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM Accentually.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(500);
  end;
  Result := True;
end;

// User settings live in %APPDATA%\Accentually; ask before removing them.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox('Also delete your Accentually settings?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\Accentually'), True, True, True);
end;
