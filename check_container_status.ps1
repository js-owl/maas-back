# Check container status
Write-Host "Checking backend container status..."
Write-Host ""

$container = docker ps -a --filter "name=backend" --format "{{.Names}} | {{.Status}} | {{.Ports}}"
if ($container) {
    Write-Host "Container found:"
    Write-Host $container
    Write-Host ""
    
    # Check if running
    $running = docker ps --filter "name=backend" --format "{{.Names}}"
    if ($running) {
        Write-Host "✅ Container is RUNNING"
    } else {
        Write-Host "❌ Container is NOT running"
        Write-Host "Starting container..."
        docker-compose -f docker-compose.local.yml up -d backend
        Start-Sleep -Seconds 2
        Write-Host "Container started"
    }
} else {
    Write-Host "❌ Container 'backend' not found"
    Write-Host "Starting with docker-compose..."
    docker-compose -f docker-compose.local.yml up -d backend
}

Write-Host ""
Write-Host "Recent logs:"
docker logs backend --tail 10





