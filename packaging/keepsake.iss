; Keepsake's Windows installer, compiled by scripts/build.py with Inno Setup 6.
; It installs for the current user only, so it never asks for an administrator.
; Built with /DTEST it installs under another name, with no shortcuts or links,
; so it can be tried on a machine that already has Keepsake.

#ifndef Version
    #error Build with scripts/build.py, which passes /DVersion and /DStage
#endif

#ifdef TEST
    #define Name "Keepsake Test"
    #define Id "{89AF076A-8193-4DD3-91CA-C319740BFF69}"
#else
    #define Name "Keepsake"
    #define Id "{E221A3C0-4045-4999-859F-EC7DC259AD14}"
#endif

[Setup]
AppId={{#Id}
AppName={#Name}
AppVersion={#Version}
AppVerName={#Name} {#Version}
AppPublisher=SomethingObvious
AppPublisherURL=https://github.com/SomethingObvious/keepsake
AppSupportURL=https://github.com/SomethingObvious/keepsake/issues
AppUpdatesURL=https://github.com/SomethingObvious/keepsake/releases
DefaultDirName={localappdata}\Programs\{#Name}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=KeepsakeSetup
SetupIconFile=..\assets\keepsake.ico
UninstallDisplayIcon={app}\app\assets\keepsake.ico
UninstallDisplayName={#Name}
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=force
LicenseFile=..\LICENSE

[Tasks]
#ifndef TEST
Name: desktopicon; Description: "Put Keepsake on the desktop"
#endif

[InstallDelete]
; The app is replaced whole, so nothing from an older version lingers.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\app.next"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

#ifndef TEST
[Icons]
Name: "{autoprograms}\Keepsake"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\keepsake.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\app\assets\keepsake.ico"; AppUserModelID: "Keepsake.Downloader"; Comment: "Download video, audio and galleries"
Name: "{autodesktop}\Keepsake"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\keepsake.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\app\assets\keepsake.ico"; AppUserModelID: "Keepsake.Downloader"; Comment: "Download video, audio and galleries"; Tasks: desktopicon

[Registry]
; Keepsake registers these itself when it starts. These lines are here so that
; uninstalling takes them away again.
Root: HKCU; Subkey: "Software\Classes\keepsake"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\Keepsake.Downloader"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Keepsake"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\keepsake.pyw"""; WorkingDir: "{app}"; Description: "Open Keepsake"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; FFmpeg, Deno and the text remover are Keepsake's own downloads. Settings,
; history and downloaded files are left alone.
Type: filesandordirs; Name: "{localappdata}\Keepsake"
#endif

[UninstallDelete]
; Updates and caches written while running.
Type: filesandordirs; Name: "{app}"
