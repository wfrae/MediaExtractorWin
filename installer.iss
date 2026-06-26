; Media Extractor — Inno Setup Installer Script
; https://jrsoftware.org/isinfo.php

[Setup]
AppName=Media Extractor
AppVersion=2.0
AppPublisher=wfrae
AppPublisherURL=https://github.com/wfrae/MediaExtractorWin
DefaultDirName={autopf}\Media Extractor
DefaultGroupName=Media Extractor
OutputDir=Output
OutputBaseFilename=MediaExtractor-Setup-v2.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MediaExtractor.exe
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MediaExtractor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Media Extractor"; Filename: "{app}\MediaExtractor.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall Media Extractor"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Media Extractor"; Filename: "{app}\MediaExtractor.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\MediaExtractor.exe"; Description: "Launch Media Extractor"; Flags: nowait postinstall skipifsilent
