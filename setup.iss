#define MyAppName "ClassPush"
#define MyAppVersion "2.1.4"
#define MyAppPublisher "Eliauk"
#define MyAppURL "https://classpush.eliauk312.top"
#define MyAppExeName "ClassPush.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{C6F77B0E-5C6D-4C6A-8A1D-3A1B6C4D5E9F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
CloseApplications=force
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
OutputDir=.
OutputBaseFilename=ClassPush_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[CustomMessages]
CreateDesktopIcon=创建桌面快捷方式(&D)
LaunchProgram=启动 ClassPush
AdditionalIcons=附加图标：

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ClassPush\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ClassPush\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Close a running ClassPush process before installation continues.
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  if ShellExec('open', 'taskkill.exe', '/F /IM ClassPush.exe', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode) then
  begin
  end;
  Result := True;
end;
