<#
.SYNOPSIS
  在没有 Docker 的 Windows 上部署本工程所需的 PostgreSQL 16。

.DESCRIPTION
  用 EDB 的免安装 binaries zip，而不是 EDB 安装器或 winget：
    - 版本与 docker-compose.yml 声明的 postgres:16-alpine 一致。验证 PG 特有行为
      （比如 ensure_schema 的事务语义）时，结论才能直接迁移到生产；
    - 不写注册表、不装系统服务、不需要交互，卸载就是删目录；
    - winget 源里只有 PostgreSQL 17/18，没有 16。

  端口用 5433 而不是默认的 5432 —— backend/app/config.py 的 database_url 就是 5433，
  装完不需要额外配 .env 就能直接跑。

  先下载（约 308 MB）：
    https://get.enterprisedb.com/postgresql/postgresql-16.10-1-windows-x64-binaries.zip

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\setup-postgres-windows.ps1 -Zip C:\tmp\pg16.zip

.NOTES
  本脚本必须存成 UTF-8 **带 BOM**。Windows PowerShell 5.1 对无 BOM 的 UTF-8 按 ANSI 解读，
  中文会乱码到破坏引号配对，脚本直接语法错。
#>
param(
  [Parameter(Mandatory = $true)][string]$Zip,
  [string]$Root = "$env:USERPROFILE\pgsql16",
  [int]$Port = 5433,
  [string]$DbName = 'agenteval',
  [string]$DbUser = 'agenteval',
  [string]$DbPass = 'agenteval'
)

$ErrorActionPreference = 'Stop'
$pgsql = Join-Path $Root 'pgsql'
$bin   = Join-Path $pgsql 'bin'
$data  = Join-Path $Root 'data'
$log   = Join-Path $Root 'pg.log'

function Step($msg) { Write-Output '' ; Write-Output ('=== ' + $msg + ' ===') }
function Bin($exe) { Join-Path $bin $exe }

# ── 1. 解压 ──────────────────────────────────────────────
# 默认装用户目录而不是 C:\ 根目录：根目录可能被系统保护策略挡住，装坏了连删都删不掉。
if (Test-Path (Join-Path $pgsql 'share\postgres.bki')) {
  Step '已存在完整二进制，跳过解压'
} else {
  Step ('解压到 ' + $Root)
  if (-not (Test-Path $Root)) { New-Item -ItemType Directory -Path $Root -Force | Out-Null }
  # 用 Windows 自带的 bsdtar，不用 Expand-Archive：后者解这个 300MB+ 的包很慢，
  # 中途中断会留下「bin 齐了但 share 没解完」的半成品，一直到 initdb 才报 postgres.bki 缺失。
  # 注意 Git Bash 里的 GNU tar 不支持 zip，必须用 System32 下的这个。
  & (Join-Path $env:SystemRoot 'System32\tar.exe') -xf $Zip -C $Root
  if ($LASTEXITCODE -ne 0) { throw ('解压失败，退出码 ' + $LASTEXITCODE) }
  foreach ($rel in @('bin\initdb.exe', 'share\postgres.bki')) {
    if (-not (Test-Path (Join-Path $pgsql $rel))) { throw ('解压不完整，缺 ' + $rel) }
  }
}
Write-Output ('  ' + (& (Bin 'postgres.exe') --version))

# ── 2. 初始化数据目录 ────────────────────────────────────
if (Test-Path (Join-Path $data 'PG_VERSION')) {
  Step '数据目录已初始化，跳过 initdb'
} else {
  Step '初始化数据目录'
  # 超级用户口令走临时文件，避免出现在命令行与进程列表里
  $pwFile = Join-Path $env:TEMP ('pgpw-' + [guid]::NewGuid().ToString('N') + '.txt')
  try {
    Set-Content -Path $pwFile -Value $DbPass -NoNewline -Encoding ascii
    # 不要在这里加 2>&1：initdb 会输出 "enabling trust authentication" 这类 warning，
    # PowerShell 5.1 把重定向后的 stderr 包成 NativeCommandError，整段就断在这儿，
    # 后面写端口配置的语句根本执行不到（实测踩过：PG 起来了却在 5432）。
    & (Bin 'initdb.exe') -D $data -U postgres --pwfile=$pwFile -E UTF8 --locale=C | Out-Null
  } finally { Remove-Item $pwFile -Force -ErrorAction SilentlyContinue }
  if (-not (Test-Path (Join-Path $data 'PG_VERSION'))) { throw 'initdb 未生成数据目录' }

  # 只监听回环：这是开发库，不对外暴露
  $conf = Join-Path $data 'postgresql.conf'
  Add-Content -Path $conf -Value '' -Encoding ascii
  Add-Content -Path $conf -Value "listen_addresses = '127.0.0.1'" -Encoding ascii
  Add-Content -Path $conf -Value ('port = ' + $Port) -Encoding ascii
}

# ── 3. 启动 ──────────────────────────────────────────────
Step ('启动 PostgreSQL（端口 ' + $Port + '）')
$status = & (Bin 'pg_ctl.exe') -D $data status
if ($status -match 'server is running') {
  Write-Output '  已在运行'
} else {
  & (Bin 'pg_ctl.exe') -D $data -l $log start | Out-Null
  Start-Sleep -Seconds 5
}
& (Bin 'pg_isready.exe') -h 127.0.0.1 -p $Port

# ── 4. 建角色与库（幂等）─────────────────────────────────
Step '创建角色与数据库'
$env:PGPASSWORD = $DbPass
$psql = Bin 'psql.exe'
$roleExists = & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DbUser'"
if ($roleExists -eq '1') {
  Write-Output ('  角色已存在 ' + $DbUser)
} else {
  & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -c "CREATE ROLE $DbUser LOGIN PASSWORD '$DbPass'" | Out-Null
  Write-Output ('  已创建角色 ' + $DbUser)
}
$dbExists = & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DbName'"
if ($dbExists -eq '1') {
  Write-Output ('  数据库已存在 ' + $DbName)
} else {
  & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres -c "CREATE DATABASE $DbName OWNER $DbUser" | Out-Null
  Write-Output ('  已创建数据库 ' + $DbName)
}

# ── 5. 以应用账号自检 ────────────────────────────────────
Step '以应用账号连通性自检'
$ver = & $psql -h 127.0.0.1 -p $Port -U $DbUser -d $DbName -tAc 'SELECT version()'
Write-Output ('  ' + $ver.Trim())
Write-Output ''
Write-Output '连接串（与 backend/app/config.py 的默认值一致，无需配 .env）：'
Write-Output ('  postgresql+psycopg2://' + $DbUser + ':' + $DbPass + '@localhost:' + $Port + '/' + $DbName)
Write-Output ('停止：' + (Bin 'pg_ctl.exe') + ' -D ' + $data + ' stop')
