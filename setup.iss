#define MyAppName "ClassPush"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Eliauk"
#define MyAppURL "https://github.com/King52HerTz/ClassPush"
#define MyAppExeName "ClassPush.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{C6F77B0E-5C6D-4C6A-8A1D-3A1B6C4D5E9F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; 开启“选择目标位置”页面 (默认是yes，所以不显示。改为no即可显示)
DisableDirPage=no
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=ClassPush_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[CustomMessages]
CreateDesktopIcon=创建桌面快捷方式(&D)
LaunchProgram=运行 ClassPush
AdditionalIcons=附加图标:

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ClassPush\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ClassPush\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 检查并关闭正在运行的进程
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  // 检测 ClassPush.exe 是否在运行
  // 这里的 'ClassPush.exe' 必须是任务管理器里看到的进程名
  // > 0 表示检测到进程
  // ShellExec 执行 taskkill 命令强行结束进程
  // /F 强制 /IM 映像名称
  if ShellExec('open', 'taskkill.exe', '/F /IM ClassPush.exe', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode) then
  begin
    // 可以在这里加日志，或者什么都不做，默默杀掉
  end;
  Result := True;
end;
