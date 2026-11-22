' Spusti PTZ IP Server bez okna konzole (systray ikonka zustane).
' POZOR: tento spoustec predpoklada, ze knihovny uz jsou nainstalovane.
' Pri PRVNIM spusteni / po reinstalaci pouzij nejdriv start_ptz.bat
' (ten chybejici knihovny websockets/pystray/pillow doinstaluje sam).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = scriptDir
sh.Run "pythonw """ & scriptDir & "\ptz_server.py""", 0, False
