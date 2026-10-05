' Double-click. Starts Python's windowed launcher, without opening a terminal.
Option Explicit
Dim shell, fso, folder, launcher, candidates, item, chosen, prefix, programs
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = fso.BuildPath(folder, "GraphPaper.pyw")
programs = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\"
candidates = Array(programs & "Python314\pythonw.exe", programs & "Python313\pythonw.exe", programs & "Python312\pythonw.exe", programs & "Python311\pythonw.exe", "C:\Python314\pythonw.exe", "C:\Python313\pythonw.exe", "C:\Python312\pythonw.exe", shell.ExpandEnvironmentStrings("%WINDIR%") & "\pyw.exe", shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Launcher\pyw.exe")
chosen = ""
For Each item In candidates
    If fso.FileExists(item) Then
        chosen = item
        Exit For
    End If
Next
If chosen = "" Then
    On Error Resume Next
    Dim proc, path
    Set proc = shell.Exec("where.exe pythonw.exe")
    If Err.Number = 0 Then
        path = Trim(proc.StdOut.ReadLine)
        If fso.FileExists(path) And InStr(1, path, "WindowsApps", 1) = 0 Then chosen = path
    End If
    On Error GoTo 0
End If
If chosen = "" Then
    MsgBox "GraphPaper needs Python 3.11 or newer for this source edition." & vbCrLf & vbCrLf & "Install Python from python.org (include Tcl/Tk and the launcher), then double-click this file again." & vbCrLf & vbCrLf & "The packaged GraphPaper.exe edition does not need a separate Python installation.", 64, "GraphPaper setup"
Else
    prefix = ""
    If LCase(fso.GetFileName(chosen)) = "pyw.exe" Then prefix = " -3"
    shell.CurrentDirectory = folder
    shell.Run Chr(34) & chosen & Chr(34) & prefix & " " & Chr(34) & launcher & Chr(34), 0, False
End If
