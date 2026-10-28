' Runs Accentually silently in the background without any console window
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strCommand = "pythonw.exe """ & strScriptDir & "\quick_accent.py"""

objShell.CurrentDirectory = strScriptDir
objShell.Run strCommand, 0, False
