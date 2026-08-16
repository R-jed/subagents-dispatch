@echo off
setlocal
if "%~1"=="" (
  echo subagents-dispatch Hook launcher requires a script path 1>&2
  exit /b 64
)
set "SCRIPT=%~1"

where py >nul 2>&1
if not errorlevel 1 (
  for %%V in (-3.11 -3) do (
    py %%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
      py %%V "%SCRIPT%"
      exit /b
    )
  )
)

for %%P in (python python3) do (
  where %%P >nul 2>&1
  if not errorlevel 1 (
    %%P -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
      %%P "%SCRIPT%"
      exit /b
    )
  )
)

echo subagents-dispatch Hook requires Python 3.11 or newer; spawn guard unavailable 1>&2
exit /b 78
