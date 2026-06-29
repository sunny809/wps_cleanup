; WPS 磁盘清理工具 - Inno Setup 安装脚本
; 在 GitHub Actions 构建流水线中使用

#define MyAppName "WPS 磁盘清理工具"
#define MyAppVersion GetEnv("GITHUB_REF_NAME")
#if MyAppVersion == ""
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "WPS Cleanup"
#define MyAppURL "https://github.com/bjdeng/wps_cleanup"
#define MyAppExeName "WPS-Cleanup.exe"

[Setup]
AppId={{B3A8F1E0-2C5D-4A6F-9E7B-8D1C3F5A7E9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=WPS-Cleanup-Setup
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:";

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im {#MyAppExeName}"; Flags: runhidden

[Code]
function InitializeUninstall: Boolean;
begin
  Result := True;
end;
