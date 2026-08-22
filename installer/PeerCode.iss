; Inno Setup script for PeerCode
; Build with: ISCC.exe PeerCode.iss  (expects dist\PeerCode.exe to exist)

#define AppName "PeerCode"
#define AppVersion "1.2.0"
#define AppPublisher "PeerCode"
#define AppExeName "PeerCode.exe"

[Setup]
AppId={{8E4B2C7A-9D1F-4B3E-A6C8-PEERCODE100}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\PeerCode.ico
OutputBaseFilename=PeerCode-Setup
OutputDir=..\dist\installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "firewall"; Description: "Allow PeerCode through Windows Firewall (recommended)"; GroupDescription: "Network:"; Flags: checkedonce

[Files]
Source: "..\dist\PeerCode.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: string;
begin
  if CurStep = ssPostInstall then begin
    if WizardIsTaskSelected('firewall') then begin
      Params := ExpandConstant('advfirewall firewall add rule name="PeerCode" dir=in action=allow program="' + ExpandConstant('{app}\{#AppExeName}') + '" enable=yes profile=any');
      ShellExec('runas', ExpandConstant('{sys}\netsh.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then begin
    ShellExec('runas', ExpandConstant('{sys}\netsh.exe'), 'advfirewall firewall delete rule name="PeerCode"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\PeerCode"
