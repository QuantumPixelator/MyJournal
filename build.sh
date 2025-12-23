#!/bin/bash
# Build script for MyJournal WPF Application
# Note: This requires Windows or Wine to build WPF applications

echo "========================================"
echo "MyJournal WPF - Build Script"
echo "========================================"
echo ""

echo "WARNING: WPF applications require Windows to build and run."
echo "This script will attempt to build, but may fail on non-Windows systems."
echo ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

echo "Restoring NuGet packages..."
dotnet restore MyJournalWPF.sln
if [ $? -ne 0 ]; then
    echo "Failed to restore packages!"
    exit 1
fi

echo ""
echo "Building solution..."
dotnet build MyJournalWPF.sln --configuration Release
if [ $? -ne 0 ]; then
    echo "Build failed!"
    echo "Note: WPF requires Windows. Use this script on Windows or with Wine."
    exit 1
fi

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo ""
echo "The application can be found in:"
echo "MyJournalWPF/bin/Release/net8.0-windows/"
echo ""
echo "To run the application:"
echo "  cd MyJournalWPF/bin/Release/net8.0-windows"
echo "  ./MyJournalWPF"
echo ""
