[Setup]
AppId=COBGDB-Python
AppName=COBGDB Python
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\COBGDB-Python
DefaultGroupName=COBGDB Python
PrivilegesRequired=lowest
MinVersion=10.0.22000
ArchitecturesAllowed=x64compatible
OutputBaseFilename=COBGDB-0.1.0-win11-x64-setup
SetupIconFile=cobgdb.ico
Compression=lzma2
SolidCompression=yes

[Files]
Source: "{#AppBinary}"; DestDir: "{app}"; DestName: "cobgdb-python-gui.exe"; Flags: ignoreversion

Source: "{#ExampleFiles}\README.md"; DestDir: "{app}\examples\gui"
Source: "{#ExampleFiles}\score.cob"; DestDir: "{app}\examples\gui"
Source: "{#ExampleFiles}\score_window.c"; DestDir: "{app}\examples\gui"

[Icons]
Name: "{group}\COBGDB Python"; Filename: "{app}\cobgdb-python-gui.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\cobgdb-python-gui.exe"; ValueType: string; ValueData: "{app}\cobgdb-python-gui.exe"; Flags: uninsdeletekey
