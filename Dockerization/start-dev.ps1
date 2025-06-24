$env:DEV_MODE = "true"
docker compose build --no-cache
if ($?) {
    docker compose up
}