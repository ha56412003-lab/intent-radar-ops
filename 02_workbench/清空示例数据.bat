@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   清空示例数据
echo ============================================
echo.
echo 这个操作会：
echo   1) 把 作品清单 works.json 清空
echo   2) 把 线索池 leads.json 清空
echo   3) 删除 data\_incoming 里的历史 CSV
echo.
echo 不会动：话术库 / 需求池 / 员工表（换行业时由行业包生成器覆盖）
echo.
set /p ok=确认清空？(输入 y 回车确认，其他键取消)：
if /i not "%ok%"=="y" (
  echo 已取消。
  pause
  exit /b
)

powershell -NoProfile -Command "[IO.File]::WriteAllText('%~dp0data\works.json','[]'); [IO.File]::WriteAllText('%~dp0data\leads.json','[]')"
del /q "%~dp0data\_incoming\*.csv" 2>nul

echo.
echo [完成] 作品清单和线索池已清空，历史 CSV 已删除。
echo 重新打开工作台即可看到干净状态。
echo.
pause
