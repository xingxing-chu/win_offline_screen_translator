' Win11 离线屏幕实时翻译助手 - 纯静默后台启动器
' 双击此脚本启动，无任何黑框命令行窗口闪烁，直接常驻右下角托盘
Set ws = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = currentDir

venvPythonw = currentDir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venvPythonw) Then
    ws.Run """" & venvPythonw & """ main.py", 0, False
Else
    ws.Run "pythonw main.py", 0, False
End If

