@echo off
echo Initializing database tables...
docker exec wellbeing-backend python /app/app/scripts/init_db.py
echo Done!
pause
