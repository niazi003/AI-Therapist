$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd "c:\Users\PC\Desktop\AI Therapist"
docker compose up --build -d