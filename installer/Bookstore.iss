#define AppName "Bookstore Management System"
#define AppVersion "1.0.0"

[Setup]
AppId={{B13658C2-0D77-4DF7-93C4-6B612A319A12}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Commonplace Books
DefaultDirName={localappdata}\Programs\Bookstore Management System
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\Bookstore.exe
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\installer-output
OutputBaseFilename=BookstoreSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "build\pyinstaller-dist\Bookstore\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Bookstore Management System"; Filename: "{app}\Bookstore.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Bookstore Management System"; Filename: "{app}\Bookstore.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\Bookstore.exe"; Description: "Launch Bookstore Management System"; Flags: postinstall nowait skipifsilent
