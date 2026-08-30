---
name: run-app
description: 打开「每日记账」桌面记账程序。用户输入 /run-app、或说"打开记账"、"启动记账"、"开一下记账 app"、任何想打开每日记账程序的时候，都要用这个技能。
---

# run-app：打开每日记账 app

## 这个技能做什么

在 Windows 上启动「每日记账」程序（Python + Tkinter + SQLite 写的本地桌面软件）。启动后屏幕上会弹出记账窗口，直接就能用。

## 怎么启动

用 PowerShell 的 `Start-Process` 命令启动，好处是：

- 命令会**立刻返回**，不会把 Claude Code 的终端卡住
- 用 `pythonw.exe` 来跑，**不会弹出黑色控制台窗口**，只显示记账界面

直接执行下面这条命令：

```powershell
Start-Process -FilePath "C:\Users\王\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe" -ArgumentList "main.py" -WorkingDirectory "D:\git仓库\Git test repository\每日记账App"
```

注意：程序路径 `D:\git仓库\Git test repository\` 里有空格，所以**不能把 main.py 的完整路径直接写进 -ArgumentList**（带空格的参数会被截断、启动失败）。正确做法就是把 `main.py` 单独传给 -ArgumentList，路径靠 -WorkingDirectory 指定，这样最稳。

## 注意事项

- **千万不要加 `-Wait` 参数**，否则 Claude Code 会一直干等着，直到把记账窗口关掉才继续。
- 启动成功后不需要任何后续操作，记账窗口自己会弹出来。
- 如果记账窗口没弹出来，把 `pythonw.exe` 换成 `python.exe` 再试一次（这样能在终端里看到报错信息），然后根据报错解决问题。
