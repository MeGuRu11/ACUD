#define MyAppName "АСУД"
#define MyAppFullName "Автоматизированная система учёта диссертаций"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ВМедА им. С.М. Кирова"
#define MyAppExeName "ASUD.exe"

[Setup]
AppId={{5A23EAE1-DBED-4B16-94B2-56A2A6AD7FD8}
AppName={#MyAppName}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppFullName}
VersionInfoProductName={#MyAppName}
DefaultDirName={localappdata}\Programs\ASUD
DefaultGroupName=АСУД
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=ASUD-Setup-{#MyAppVersion}
SetupIconFile=..\assets\asud_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
WizardImageFile=assets\wizard-large.bmp
WizardSmallImageFile=assets\wizard-small.bmp
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
MinVersion=10.0.17763
UsePreviousAppDir=yes
UsePreviousTasks=yes
ShowLanguageDialog=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Messages]
WelcomeLabel1=Добро пожаловать в мастер установки АСУД
WelcomeLabel2=Мастер установит автоматизированную систему учёта диссертаций на этот компьютер.%n%nНа новом устройстве приложение запустится с чистой базой данных и предложит создать первого администратора.
SelectDirLabel3=Мастер установит АСУД в следующую папку.
ReadyLabel1=Мастер готов начать установку АСУД.
FinishedHeadingLabel=Установка АСУД завершена
FinishedLabel=АСУД установлена на этот компьютер.%n%nРабочие данные хранятся отдельно в профиле пользователя и не включаются в установочный пакет.

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"; Flags: checkedonce

[Files]
Source: "..\dist\ASUD.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\АСУД"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{#MyAppFullName}"
Name: "{autodesktop}\АСУД"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{#MyAppFullName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить АСУД"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Font.Name := 'Segoe UI';
  WizardForm.WelcomeLabel1.Font.Size := 18;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.WelcomeLabel2.Font.Name := 'Segoe UI';
  WizardForm.WelcomeLabel2.Font.Size := 10;
  WizardForm.FinishedHeadingLabel.Font.Name := 'Segoe UI';
  WizardForm.FinishedHeadingLabel.Font.Size := 16;
  WizardForm.FinishedHeadingLabel.Font.Style := [fsBold];
end;
