@echo off
REM Build script for MyJournal WPF Application
REM Run this on Windows with .NET 8 SDK installed

echo ========================================
echo MyJournal WPF - Build Script
echo ========================================
echo.

echo Restoring NuGet packages...
dotnet restore MyJournalWPF.sln
if %errorlevel% neq 0 (
    echo Failed to restore packages!
    pause
    exit /b %errorlevel%
)

echo.
echo Building solution...
dotnet build MyJournalWPF.sln --configuration Release
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo The application can be found in:
echo MyJournalWPF\bin\Release\net8.0-windows\
echo.
echo To run the application:
echo   cd MyJournalWPF\bin\Release\net8.0-windows
echo   MyJournalWPF.exe
echo.
pause
