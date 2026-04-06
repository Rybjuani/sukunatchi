#define MyAppName "Sukunatchi"
#define MyAppPublisher "Rybjuani"
#define MyAppURL "https://github.com/Rybjuani/sukunatchi"

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#ifndef SourceExe
  #define SourceExe "dist\Sukunatchi.exe"
#endif

[Setup]
AppId={{4E53D273-0331-4F96-8C63-2A8C4D798D4D}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer-dist
OutputBaseFilename=Sukunatchi-Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Sukunatchi.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\Sukunatchi"; Filename: "{app}\Sukunatchi.exe"
Name: "{userprograms}\Sukunatchi"; Filename: "{app}\Sukunatchi.exe"

[Run]
Filename: "{app}\Sukunatchi.exe"; Description: "Launch Sukunatchi"; Flags: nowait postinstall skipifsilent
