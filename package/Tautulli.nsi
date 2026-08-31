############################################################################################
#      NSIS Installation Script created by NSIS Quick Setup Script Generator v1.09.18
#               Entirely Edited with NullSoft Scriptable Installation System                
#              by Vlasis K. Barkas aka Red Wine red_wine@freemail.gr Sep 2006               
############################################################################################

!define APP_NAME "Tautulli"
!define COMP_NAME "Tautulli"
!define WEB_SITE "https://tautulli.com"
!define COPYRIGHT "Tautulli © 2025"
!define DESCRIPTION "Monitor your Plex Media Server"
!define APP_ICON "..\dist\Tautulli\data\interfaces\default\images\logo-circle.ico"
!define LICENSE_TXT "..\dist\Tautulli\LICENSE"
!define MAIN_APP_EXE "Tautulli.exe"
!define INSTALL_TYPE "SetShellVarContext current"
!define REG_ROOT "HKCU"
!define REG_APP_PATH "Software\Microsoft\Windows\CurrentVersion\App Paths\${MAIN_APP_EXE}"
!define UNINSTALL_PATH "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

!define REG_START_MENU "Start Menu Folder"

var SM_Folder

######################################################################

VIProductVersion  "${VERSION}"
VIAddVersionKey "ProductName"  "${APP_NAME}"
VIAddVersionKey "CompanyName"  "${COMP_NAME}"
VIAddVersionKey "LegalCopyright"  "${COPYRIGHT}"
VIAddVersionKey "FileDescription"  "${DESCRIPTION}"
VIAddVersionKey "FileVersion"  "${VERSION}"

######################################################################

Unicode True
SetCompressor ZLIB
Name "${APP_NAME}"
Caption "${APP_NAME}"
OutFile "${INSTALLER_NAME}"
BrandingText "${APP_NAME}"
XPStyle on
InstallDirRegKey "${REG_ROOT}" "${REG_APP_PATH}" ""
InstallDir "$PROGRAMFILES64\${APP_NAME}"

######################################################################

!define nsProcess::FindProcess `!insertmacro nsProcess::FindProcess`

!macro nsProcess::FindProcess _FILE _ERR
	nsProcess::_FindProcess /NOUNLOAD `${_FILE}`
	Pop ${_ERR}
!macroend


!define nsProcess::KillProcess `!insertmacro nsProcess::KillProcess`

!macro nsProcess::KillProcess _FILE _ERR
	nsProcess::_KillProcess /NOUNLOAD `${_FILE}`
	Pop ${_ERR}
!macroend

!define nsProcess::CloseProcess `!insertmacro nsProcess::CloseProcess`

!macro nsProcess::CloseProcess _FILE _ERR
	nsProcess::_CloseProcess /NOUNLOAD `${_FILE}`
	Pop ${_ERR}
!macroend


!define nsProcess::Unload `!insertmacro nsProcess::Unload`

!macro nsProcess::Unload
	nsProcess::_Unload
!macroend

######################################################################

!include Sections.nsh

Var /GLOBAL createDesktopShortcut
Var /GLOBAL skipLaunch
Var /GLOBAL skipBrowser
Var desktopShortcutCheckbox

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"
!include "Util.nsh"
!include "WinMessages.nsh"
!addplugindir nsis-plugins\x86-unicode

!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

!define MUI_ICON "${APP_ICON}"

!insertmacro MUI_PAGE_WELCOME

!ifdef LICENSE_TXT
!insertmacro MUI_PAGE_LICENSE "${LICENSE_TXT}"
!endif

!ifdef REG_START_MENU
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${APP_NAME}"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "${REG_ROOT}"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${UNINSTALL_PATH}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "${REG_START_MENU}"
!insertmacro MUI_PAGE_STARTMENU Application $SM_Folder
!endif

!insertmacro MUI_PAGE_DIRECTORY

Page custom CustomizePage CustomizePageLeave

!insertmacro MUI_PAGE_INSTFILES

!define MUI_PAGE_CUSTOMFUNCTION_SHOW FinishPageShow
!define MUI_FINISHPAGE_RUN "$INSTDIR\${MAIN_APP_EXE}"
!define MUI_FINISHPAGE_RUN_PARAMETERS $skipBrowser
!insertmacro MUI_PAGE_FINISH

Function FinishPageShow
  ${If} $skipLaunch == 1
    ${NSD_Uncheck} $mui.FinishPage.Run
  ${EndIf}
FunctionEnd

!insertmacro MUI_UNPAGE_CONFIRM

!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

######################################################################

Section -MainProgram
Call UninstallPrevious

${INSTALL_TYPE}
SetOverwrite on
SetOutPath "$INSTDIR"
File /nonfatal /a /r "..\dist\${APP_NAME}\"

IfSilent 0 +3
StrCmp $skipLaunch 1 +2 0
ExecShell "" "$INSTDIR\${MAIN_APP_EXE}" $skipBrowser
SectionEnd

######################################################################

Section -Icons_Reg
SetOutPath "$INSTDIR"
WriteUninstaller "$INSTDIR\uninstall.exe"

!ifdef REG_START_MENU
!insertmacro MUI_STARTMENU_WRITE_BEGIN Application
CreateDirectory "$SMPROGRAMS\$SM_Folder"
CreateShortCut "$SMPROGRAMS\$SM_Folder\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
${If} $createDesktopShortcut == 1
CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
${EndIf}
CreateShortCut "$SMPROGRAMS\$SM_Folder\Uninstall ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"

!ifdef WEB_SITE
WriteIniStr "$INSTDIR\${APP_NAME} website.url" "InternetShortcut" "URL" "${WEB_SITE}"
CreateShortCut "$SMPROGRAMS\$SM_Folder\${APP_NAME} Website.lnk" "$INSTDIR\${APP_NAME} website.url"
!endif
!insertmacro MUI_STARTMENU_WRITE_END
!endif

!ifndef REG_START_MENU
CreateDirectory "$SMPROGRAMS\${APP_NAME}"
CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
${If} $createDesktopShortcut == 1
CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
${EndIf}
CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"

!ifdef WEB_SITE
WriteIniStr "$INSTDIR\${APP_NAME} website.url" "InternetShortcut" "URL" "${WEB_SITE}"
CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} Website.lnk" "$INSTDIR\${APP_NAME} website.url"
!endif
!endif

WriteRegStr ${REG_ROOT} "${REG_APP_PATH}" "" "$INSTDIR\${MAIN_APP_EXE}"
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayName" "${APP_NAME}"
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "UninstallString" "$INSTDIR\uninstall.exe"
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayIcon" "$INSTDIR\${MAIN_APP_EXE}"
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayVersion" "${VERSION}"
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "Publisher" "${COMP_NAME}"

!ifdef WEB_SITE
WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "URLInfoAbout" "${WEB_SITE}"
!endif
SectionEnd

######################################################################

Section Uninstall
${INSTALL_TYPE}
Delete "$INSTDIR\uninstall.exe"
!ifdef WEB_SITE
Delete "$INSTDIR\${APP_NAME} website.url"
!endif

RmDir /r "$INSTDIR"
RmDir "$INSTDIR"

!ifdef REG_START_MENU
!insertmacro MUI_STARTMENU_GETFOLDER "Application" $SM_Folder
Delete "$SMPROGRAMS\$SM_Folder\${APP_NAME}.lnk"
Delete "$SMPROGRAMS\$SM_Folder\Uninstall ${APP_NAME}.lnk"
!ifdef WEB_SITE
Delete "$SMPROGRAMS\$SM_Folder\${APP_NAME} Website.lnk"
!endif
${If} $createDesktopShortcut == 1
Delete "$DESKTOP\${APP_NAME}.lnk"
${EndIf}

RmDir "$SMPROGRAMS\$SM_Folder"
!endif

!ifndef REG_START_MENU
Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
!ifdef WEB_SITE
Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME} Website.lnk"
!endif
${If} $createDesktopShortcut == 1
Delete "$DESKTOP\${APP_NAME}.lnk"
${EndIf}

RmDir "$SMPROGRAMS\${APP_NAME}"
!endif

DeleteRegKey ${REG_ROOT} "${REG_APP_PATH}"
DeleteRegKey ${REG_ROOT} "${UNINSTALL_PATH}"
SectionEnd

######################################################################

Function .onInit
  ; Set default value for desktop shortcut (1 = create, 0 = don't create)
  StrCpy $createDesktopShortcut 0
  
  ; Set default value for skip launch (0 = launch, 1 = skip)
  StrCpy $skipLaunch 0
  
  ; Set default value for skip browser
  StrCpy $skipBrowser ""
  
  ; Check for /NOLAUNCH flag
  ${GetParameters} $0
  ${GetOptions} $0 "/NOLAUNCH" $1
  ${If} ${Errors}
    ; No /NOLAUNCH flag found
  ${Else}
    ; /NOLAUNCH flag found, skip launch
    StrCpy $skipLaunch 1
  ${EndIf}
  
  ; Check for /NOBROWSER flag
  ${GetParameters} $0
  ${GetOptions} $0 "/NOBROWSER" $1
  ${If} ${Errors}
    ; No /NOBROWSER flag found
  ${Else}
    ; /NOBROWSER flag found, skip browser
    StrCpy $skipBrowser "--nolaunch"
  ${EndIf}
  
  IfSilent 0 +2
  StrCpy $skipBrowser "--nolaunch"
  
  IfSilent +5 0
  Loop:
    ${nsProcess::FindProcess} ${MAIN_APP_EXE} $R0
    StrCmp $R0 0 0 NoAbort
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is still running. Please shutdown ${APP_NAME} before continuing." IDCANCEL End IDRETRY Loop
  Goto Loop
  End:
	Abort
  NoAbort:
FunctionEnd

Function un.onInit
  IfSilent +5 0
  Loop:
    ${nsProcess::FindProcess} ${MAIN_APP_EXE} $R0
    StrCmp $R0 0 0 NoAbort
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is still running. Please shutdown ${APP_NAME} before continuing." IDCANCEL End IDRETRY Loop
  Goto Loop
  End:
	Abort
  NoAbort:
FunctionEnd

######################################################################

Function UninstallPrevious
  ; Check for uninstaller.
  ReadRegStr $R0 "${REG_ROOT}" "${UNINSTALL_PATH}" "UninstallString"
  ${If} $R0 == ""
    Goto Done
  ${EndIf}
  DetailPrint "Removing previous installation."
  ; Run the uninstaller silently.
  ExecWait '"$R0" /S _?=$INSTDIR'
  Done:
FunctionEnd

######################################################################

Function CustomizePage
  !insertmacro MUI_HEADER_TEXT "Installation Options" "Choose installation options"
  
  nsDialogs::Create 1018
  Pop $0
  
  ${NSD_CreateCheckbox} 10u 10u 90% 12u "Create Desktop Shortcut"
  Pop $desktopShortcutCheckbox
  ${NSD_SetState} $desktopShortcutCheckbox $createDesktopShortcut
  
  nsDialogs::Show
FunctionEnd

Function CustomizePageLeave
  ${NSD_GetState} $desktopShortcutCheckbox $createDesktopShortcut
FunctionEnd

######################################################################
