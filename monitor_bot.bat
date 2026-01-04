@echo off
echo ========================================
echo   Discord Bot Monitor
echo ========================================
echo.
echo Bot is running. Watching logs...
echo Press Ctrl+C to stop
echo.
docker logs -f stock-discord-bot
