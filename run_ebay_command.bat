@echo off
REM Batch file to run eBay commands with proper argument handling
REM This helps avoid issues with special characters in Windows Command Prompt

if "%1"=="" (
    echo Usage: run_ebay_command.bat ^<command^> [args...]
    echo Commands: search, seller, item, collect, process, top, copy, refresh
    echo.
    echo For arguments with special characters, use quotes:
    echo run_ebay_command.bat search "item with ^ and | characters"
    exit /b 1
)

REM Pass all arguments to Python script
python ebay_search_test.py %*
