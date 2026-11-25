; Inno Setup script for Blackbyrd3D.
; Compile after the PyInstaller build:
;   ISCC.exe installer.iss

#define AppName "Blackbyrd3D"
#define AppPublisher "Jonas Pedrotti"
#define AppURL "https://github.com/JonasPedrotti/Blackbyrd3D"

; The version is not written here. make_version_info.py puts the one in
; pyproject.toml into byrd3d.exe, and the installer reads it back out, so
; the installer, the app and the SignPath signing request cannot disagree.
#define AppExe AddBackslash(SourcePath) + "dist\byrd3d\byrd3d.exe"
#if !FileExists(AppExe)
  #error Build byrd3d.exe with PyInstaller before compiling the installer
#endif
; GetStringFileInfo, not the GetFileProductVersionString helper: that one
; only exists in newer Inno Setup releases than the runner's 6.7.1.
#define AppVersion GetStringFileInfo(AppExe, "ProductVersion")
#if AppVersion == ""
  #error byrd3d.exe carries no ProductVersion; see make_version_info.py
#endif

[Setup]
AppId={{22565D17-2D0E-4FC0-B968-DA38B481A572}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoProductTextVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright=MIT Licensed. Copyright (c) {#AppPublisher}.
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\byrd3d.exe
LicenseFile=..\..\LICENSE
; SignPath Foundation's terms: anything sent to a system the user did not
; choose (the update check) must be described during installation
InfoBeforeFile=privacy.txt
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=Blackbyrd3D-Setup-x86_64
Compression=lzma2
SolidCompression=yes
; Dressed like the app: the dark style's title bar grey behind every page so
; window and page are one colour, the splash beside the first and last page,
; its mark in the corner of the rest
WizardStyle=modern dark hidebevels includetitlebar
WizardBackColor=#2b2b2b
WizardSmallImageBackColor=none
WizardSizePercent=120,100
WizardImageFile=wizard\wizard-*x*.png
WizardSmallImageFile=wizard\wizard-small-*.png
SetupIconFile=byrd3d.ico
DisableWelcomePage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; \
  GroupDescription: "Additional icons:"; Flags: unchecked
Name: "updatecheck"; Description: "Check GitHub for &updates on startup"; \
  GroupDescription: "Options:"
Name: "fileassoc"; \
  Description: "Make Blackbyrd3D the &default app for .byrd and .wyrm files"; \
  GroupDescription: "Options:"

[InstallDelete]
; An update copies over the old install, so files a newer build no longer
; ships stayed behind. A stale blackbyrd3d-*.dist-info made 0.3.0 report 0.2.1.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\byrd3d\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "wyrm.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\byrd3d.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\byrd3d.exe"; \
  Tasks: desktopicon

[Registry]
; Ours by default when the task is ticked, as Explorer shows a file's icon
; from the type it defaults to. Without it we are only in "Open with".
Root: HKA; Subkey: "Software\Classes\.byrd"; \
  ValueType: string; ValueName: ""; ValueData: "Blackbyrd3D.Document"; \
  Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.byrd\OpenWithProgids"; \
  ValueType: string; ValueName: "Blackbyrd3D.Document"; ValueData: ""; \
  Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Document"; \
  ValueType: string; ValueName: ""; ValueData: "Blackbyrd3D model"; \
  Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Document\DefaultIcon"; \
  ValueType: string; ValueName: ""; ValueData: "{app}\byrd3d.exe,0"
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Document\shell\open\command"; \
  ValueType: string; ValueName: ""; ValueData: """{app}\byrd3d.exe"" ""%1"""
; A Wyrm graph wears Wyrm's logo, and opens in Wyrm beside the model.
Root: HKA; Subkey: "Software\Classes\.wyrm"; \
  ValueType: string; ValueName: ""; ValueData: "Blackbyrd3D.Wyrm"; \
  Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.wyrm\OpenWithProgids"; \
  ValueType: string; ValueName: "Blackbyrd3D.Wyrm"; ValueData: ""; \
  Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Wyrm"; \
  ValueType: string; ValueName: ""; ValueData: "Wyrm graph"; \
  Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Wyrm\DefaultIcon"; \
  ValueType: string; ValueName: ""; ValueData: "{app}\wyrm.ico"
Root: HKA; Subkey: "Software\Classes\Blackbyrd3D.Wyrm\shell\open\command"; \
  ValueType: string; ValueName: ""; ValueData: """{app}\byrd3d.exe"" ""%1"""

; The app reads this to not ask again what the installer already asked
Root: HKA; Subkey: "Software\Blackbyrd3D"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Blackbyrd3D"; \
  ValueType: dword; ValueName: "AssociateFiles"; ValueData: 1; \
  Tasks: fileassoc
Root: HKA; Subkey: "Software\Blackbyrd3D"; \
  ValueType: dword; ValueName: "AssociateFiles"; ValueData: 0; \
  Tasks: not fileassoc

[Run]
Filename: "{app}\byrd3d.exe"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[Code]
{ The "check for updates" task is applied to settings.json on every install,
  ticked or cleared - SignPath's terms require an opt-out at install time, not
  only a runtime setting. Ticking it again must also undo an earlier opt-out,
  so an existing file gets its check_updates value flipped in place; the rest
  of the file is left as it is. }
procedure ApplyUpdateCheck;
var
  CfgDir, CfgPath: String;
  Json, Wanted, Other: AnsiString;
  P: Integer;
begin
  CfgDir := ExpandConstant('{%USERPROFILE}') + '\.config\blackbyrd3d';
  CfgPath := CfgDir + '\settings.json';
  if WizardIsTaskSelected('updatecheck') then
  begin
    Wanted := '"check_updates": true';
    Other := '"check_updates": false';
  end else begin
    Wanted := '"check_updates": false';
    Other := '"check_updates": true';
  end;
  if FileExists(CfgPath) then
  begin
    if not LoadStringFromFile(CfgPath, Json) then
      Exit;
    P := Pos(Other, Json);
    if P > 0 then
      Json := Copy(Json, 1, P - 1) + Wanted + Copy(Json, P + Length(Other), MaxInt)
    else if (Pos('"check_updates"', Json) = 0) and
            (not WizardIsTaskSelected('updatecheck')) then
    begin
      P := Pos('{', Json);
      if P = 0 then
        Exit;
      Insert(#13#10 + '  ' + Wanted + ',', Json, P + 1);
    end else
      Exit;
    SaveStringToFile(CfgPath, Json, False);
  end
  else if not WizardIsTaskSelected('updatecheck') then
  begin
    ForceDirectories(CfgDir);
    SaveStringToFile(CfgPath,
      '{' + #13#10 + '  "check_updates": false' + #13#10 + '}' + #13#10,
      False);
  end;
end;

const
  FileExts = 'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\';

{ Ticked: a choice once made in Settings (UserChoice) would still beat the
  class registered above, so it is cleared. Cleared: an earlier install may
  have made us the default, which is taken back, but only where it is ours. }
procedure ApplyFileAssoc(Ext, ProgId: String);
var
  Current: String;
begin
  if WizardIsTaskSelected('fileassoc') then
  begin
    RegDeleteKeyIncludingSubkeys(HKCU, FileExts + Ext + '\UserChoice');
    RegDeleteKeyIncludingSubkeys(HKCU, FileExts + Ext + '\UserChoiceLatest');
  end
  else if RegQueryStringValue(HKA, 'Software\Classes\' + Ext, '', Current) and
          (Current = ProgId) then
    RegDeleteValue(HKA, 'Software\Classes\' + Ext, '');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep <> ssPostInstall then
    Exit;
  ApplyUpdateCheck;
  ApplyFileAssoc('.byrd', 'Blackbyrd3D.Document');
  ApplyFileAssoc('.wyrm', 'Blackbyrd3D.Wyrm');
end;

{ Page layout: the text on the Welcome, options and Finished pages sits in
  the middle of its page rather than at the top. }

{ The window is lower than modern style's default (WizardSizePercent), which
  would narrow the picture beside the Welcome and Finished pages with it. It
  keeps its width instead, drawn 202:314 by make_wizard_images.py, and the
  text beside it moves over to make room. }
procedure MakeRoom(C: TControl; Delta: Integer);
begin
  C.Left := C.Left + Delta;
  C.Width := C.Width - Delta;
end;

procedure InitializeWizard;
var
  F: TWizardForm;
  Delta: Integer;
begin
  F := WizardForm;
  Delta := F.WizardBitmapImage.Height * 202 div 314 - F.WizardBitmapImage.Width;
  F.WizardBitmapImage.Width := F.WizardBitmapImage.Width + Delta;
  F.WizardBitmapImage2.Width := F.WizardBitmapImage2.Width + Delta;
  MakeRoom(F.WelcomeLabel1, Delta);
  MakeRoom(F.WelcomeLabel2, Delta);
  MakeRoom(F.FinishedHeadingLabel, Delta);
  MakeRoom(F.FinishedLabel, Delta);
  MakeRoom(F.RunList, Delta);
  MakeRoom(F.YesRadio, Delta);
  MakeRoom(F.NoRadio, Delta);
end;

{ A list as tall as its rows, so it can be centred with the text above it. }
procedure FitList(List: TNewCheckListBox);
begin
  List.Height := List.Items.Count * ScaleY(22) + ScaleY(4);
end;

{ Moves Top and Bottom, the first and last control of a stack, so the stack
  is centred in Area; whatever lies between them moves with them. }
procedure CentreStack(Top, Bottom: TControl; Area: Integer);
var
  Shift: Integer;
begin
  Shift := (Area - (Bottom.Top + Bottom.Height - Top.Top)) div 2 - Top.Top;
  Top.Top := Top.Top + Shift;
  if Bottom <> Top then
    Bottom.Top := Bottom.Top + Shift;
end;

procedure CentreThree(A, B, C: TControl; Area: Integer);
var
  Shift: Integer;
begin
  Shift := (Area - (C.Top + C.Height - A.Top)) div 2 - A.Top;
  A.Top := A.Top + Shift;
  B.Top := B.Top + Shift;
  C.Top := C.Top + Shift;
end;

{ Label as tall as its text, now that MakeRoom may have wrapped it, and
  Below as far under it as it was. }
procedure FitText(L: TNewStaticText; Below: TControl);
var
  Gap: Integer;
begin
  Gap := Below.Top - L.Top - L.Height;
  L.AdjustHeight;
  Below.Top := L.Top + L.Height + Gap;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  F: TWizardForm;
  LabelTop: Integer;
begin
  F := WizardForm;
  F.WizardSmallBitmapImage.Visible := CurPageID <> wpSelectTasks;
  case CurPageID of
    wpWelcome:
      begin
        FitText(F.WelcomeLabel1, F.WelcomeLabel2);
        F.WelcomeLabel2.AdjustHeight;
        CentreStack(F.WelcomeLabel1, F.WelcomeLabel2, F.WelcomePage.ClientHeight);
      end;
    wpSelectTasks:
      begin
        FitList(F.TasksList);
        CentreStack(F.SelectTasksLabel, F.TasksList, F.SelectTasksPage.ClientHeight);
      end;
    wpFinished:
      begin
        LabelTop := F.FinishedLabel.Top;
        FitText(F.FinishedHeadingLabel, F.FinishedLabel);
        if F.RunList.Visible then
        begin
          F.RunList.Top := F.RunList.Top + F.FinishedLabel.Top - LabelTop;
          FitText(F.FinishedLabel, F.RunList);
          FitList(F.RunList);
          CentreThree(F.FinishedHeadingLabel, F.FinishedLabel, F.RunList,
                      F.FinishedPage.ClientHeight);
        end else
        begin
          F.FinishedLabel.AdjustHeight;
          CentreStack(F.FinishedHeadingLabel, F.FinishedLabel,
                      F.FinishedPage.ClientHeight);
        end;
      end;
  end;
end;
