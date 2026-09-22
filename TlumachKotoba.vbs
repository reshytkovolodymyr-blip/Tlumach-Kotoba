' TlumachKotoba.vbs
' ------------------
' Запуск застосунку БЕЗ вікна командного рядка (CMD) — жодного
' вікна консолі не з'являється навіть на мить. Використовує pyw
' (той самий Python, що й py, але без консолі за задумом Windows).
'
' Це основний спосіб щоденного запуску. START_APP.bat лишається
' окремо, спеціально для діагностики: якщо щось не встановлено чи
' сталася помилка, .bat покаже текст помилки у видимому вікні, а
' цей .vbs — ні (помилка буде не видно користувачу).

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = scriptDir
shell.Run "pyw """ & scriptDir & "\tlumach_kotoba.py""", 0, False
