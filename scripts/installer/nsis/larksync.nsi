; LarkSync NSIS installer script
; Build: makensis /DAPP_VERSION=... /DPROJECT_ROOT=... larksync.nsi

!include "MUI2.nsh"
!include "nsDialogs.nsh"

!define APP_NAME "LarkSync"
!define APP_PUBLISHER "LarkSync"
!define APP_EXE "LarkSync.exe"

!ifndef APP_VERSION
!define APP_VERSION "0.0.0"
!endif

!define /redef PROJECT_ROOT "${__FILEDIR__}\..\..\.."
!define /redef SOURCE_DIR "${PROJECT_ROOT}\dist\LarkSync"
!define /redef APP_ICON "${PROJECT_ROOT}\assets\branding\LarkSync.ico"

Name "${APP_NAME}"
OutFile "${PROJECT_ROOT}/dist/${APP_NAME}-Setup-${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES64\\${APP_NAME}"
InstallDirRegKey HKLM "Software\\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
Unicode True
SetCompressor /SOLID lzma

; ---- UI ----
!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_FINISHPAGE_RUN "$INSTDIR\\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "立即启动 LarkSync"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; ---- 全局变量 ----
Var DeleteUserData

; ---- 安装前关闭运行中的实例 ----
Function .onInit
  ; 尝试关闭正在运行的 LarkSync 进程，确保覆盖安装成功
  ExecWait 'taskkill /F /IM "${APP_EXE}" /T'
  ; 等待进程完全退出
  Sleep 1000
FunctionEnd

Section "Main" SecMain
  SetOutPath "$INSTDIR"
  File /r "${SOURCE_DIR}\*.*"

  WriteRegStr HKLM "Software\\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\\${APP_NAME}" "Version" "${APP_VERSION}"

  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\${APP_EXE}" 0
  CreateShortcut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\${APP_EXE}" 0

  WriteUninstaller "$INSTDIR\\Uninstall.exe"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
SectionEnd

; ---- 卸载前关闭运行中的实例 + 询问是否保留用户数据 ----
Function un.onInit
  ExecWait 'taskkill /F /IM "${APP_EXE}" /T'
  Sleep 1000

  ; 默认保留用户数据
  StrCpy $DeleteUserData "0"

  MessageBox MB_YESNO|MB_ICONQUESTION \
    "是否同时删除用户数据（配置、数据库、日志、登录凭证）？$\r$\n$\r$\n选择「否」可在重新安装后保留登录状态和同步配置。" \
    IDYES _setDelete IDNO _setKeep

  _setDelete:
    StrCpy $DeleteUserData "1"
    Goto _doneAsk
  _setKeep:
    StrCpy $DeleteUserData "0"
  _doneAsk:
FunctionEnd

Section "Uninstall"
  ; 1. 删除快捷方式
  Delete "$DESKTOP\\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"

  ; 2. 删除安装目录
  Delete "$INSTDIR\\Uninstall.exe"
  RMDir /r "$INSTDIR"

  ; 3. 删除注册表项
  DeleteRegKey HKLM "Software\\${APP_NAME}"
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"

  ; 4. 按用户选择决定是否删除用户数据
  StrCmp $DeleteUserData "1" 0 skipClean

    ; 删除 %APPDATA%\LarkSync 目录（config.json、larksync.db、logs 等）
    RMDir /r "$APPDATA\\${APP_NAME}"

    ; 清除 Windows 凭据管理器中的 OAuth 令牌（静默忽略错误）
    ExecWait 'cmdkey /delete:larksync:access_token'
    ExecWait 'cmdkey /delete:larksync:refresh_token'
    ExecWait 'cmdkey /delete:larksync:expires_at'
    ExecWait 'cmdkey /delete:larksync:oauth_tokens'

  skipClean:
SectionEnd
