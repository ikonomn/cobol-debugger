[Setup]
AppId=COBOL-Debugger
AppName=COBOL Debugger
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\COBOL-Debugger
DefaultGroupName=COBOL Debugger
PrivilegesRequired=lowest
MinVersion=10.0.22000
ArchitecturesAllowed=x64compatible
OutputBaseFilename=COBOL-Debugger-0.1.0-win11-x64-setup
SetupIconFile=cobgdb.ico
Compression=lzma2
SolidCompression=yes

[Files]
Source: "{#AppBinary}"; DestDir: "{app}"; DestName: "cobol-debugger.exe"; Flags: ignoreversion

Source: "{#ExampleFiles}\*"; DestDir: "{app}\examples"; Flags: recursesubdirs

[Icons]
Name: "{group}\COBOL Debugger"; Filename: "{app}\cobol-debugger.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\cobol-debugger.exe"; ValueType: string; ValueData: "{app}\cobol-debugger.exe"; Flags: uninsdeletekey
