# 装 ego(lite) 并让 ego-browser 可用（Windows）
# 用法（在本目录下，普通 PowerShell 窗口）：
#   powershell -ExecutionPolicy Bypass -File install_windows.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$setup = Join-Path $here "egoliteSetup.exe"

Write-Host "===== ego(lite) 一键安装 =====" -ForegroundColor Green

# ① 已经装过就跳过下载
$cli = $null
foreach ($base in @("$env:ProgramFiles\Citro Labs\ego lite\Application", "$env:LOCALAPPDATA\Programs\Citro Labs\ego lite\Application")) {
    if (Test-Path $base) {
        $cli = Get-ChildItem $base -Recurse -Filter "ego-browser.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
        if ($cli) { break }
    }
}

if (-not $cli) {
    if (-not (Test-Path $setup)) { Write-Error "缺少 egoliteSetup.exe（应和本脚本同目录）"; exit 1 }
    Write-Host "[1/4] 静默安装 ego(lite)…（可能弹 UAC，请点「是」）"
    $p = Start-Process -FilePath $setup -ArgumentList "/S" -Wait -PassThru
    Write-Host "      安装器退出码: $($p.ExitCode)"
    Start-Sleep -Seconds 3
    foreach ($base in @("$env:ProgramFiles\Citro Labs\ego lite\Application", "$env:LOCALAPPDATA\Programs\Citro Labs\ego lite\Application")) {
        if (Test-Path $base) {
            $cli = Get-ChildItem $base -Recurse -Filter "ego-browser.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
            if ($cli) { break }
        }
    }
} else {
    Write-Host "[1/4] 已装过，跳过安装"
}

if (-not $cli) { Write-Error "没找到 ego-browser.exe。请手动从 https://lite.ego.app 安装后重跑。"; exit 1 }
Write-Host "      ego-browser = $($cli.FullName)"

# ② 把 CLI 路径记进项目，run.py 会自动读
$pathFile = Join-Path (Split-Path (Split-Path $here -Parent) -Parent) "06_agent-skill\.ego-path"
if ($here -notlike "*06_agent-skill*") { $pathFile = Join-Path $here "..\.ego-path" }
try {
    Set-Content -Path $pathFile -Value $cli.FullName -Encoding UTF8
    Write-Host "[2/4] 已记录路径 -> $pathFile"
} catch { Write-Host "[2/4] 记录路径失败（不影响使用，可用 --ego 指定）" }

# ③ 启动并等人工完成 onboarding
Write-Host "[3/4] 启动 ego(lite)…"
$egoExe = Join-Path (Split-Path $cli.FullName -Parent | Split-Path -Parent) "ego.exe"
if (Test-Path $egoExe) { Start-Process $egoExe; Start-Sleep -Seconds 6 }

$probe = & $cli.FullName nodejs -e "console.log('ok')" 2>&1 | Out-String
if ($probe -match "onboarding") {
    Write-Host ""
    Write-Host "⚠ 需要你手动完成一次引导（约 30 秒）：" -ForegroundColor Yellow
    Write-Host "   在那个 ego 窗口里点几下就行；导入 Chrome 数据建议选「稍后设置」。"
    Read-Host "   完成后按回车继续"
    Start-Sleep -Seconds 2
    $probe = & $cli.FullName nodejs -e "console.log('ok')" 2>&1 | Out-String
}

# ④ 验收
Write-Host "[4/4] 验收："
if ($probe -match "ok") {
    Write-Host "      ✓ ego-browser 可用" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步：python scripts\run.py --keyword 云南旅游 --videos 2 --rounds 2" -ForegroundColor Cyan
} else {
    Write-Host "      ✗ 还不可用，输出如下：" -ForegroundColor Red
    Write-Host $probe
    Write-Host "      → 确保引导已走完，然后新开一个终端重跑本脚本"
}
