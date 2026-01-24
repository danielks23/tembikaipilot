# Web Monitor Playback Guide

## Features

The web monitor now includes **automatic data logging** and **playback functionality** to replay past driving sessions!

## How It Works

### 1. Automatic Logging
When you run `web_monitor_server.py`, it automatically logs all data to JSONL files:
- **Location**: `/data/web_monitor_logs/` on KA2 (or `./web_monitor_logs/` on PC)
- **Format**: `drive_YYYYMMDD_HHMMSS.jsonl` (e.g., `drive_20260124_143022.jsonl`)
- **Frequency**: Data saved at 10 Hz (every 100ms)
- **Auto-flush**: Writes to disk every 5 seconds or 50 entries
- **Resource Usage**: < 1% CPU, ~5-10 MB RAM

### 2. Playback Controls

In the web interface (`http://<KA2_IP>:8080`), you'll see **Playback Controls** at the top:

#### Loading a Log
1. Click **🔄 Refresh Logs** to see all available recordings
2. Select a log from dropdown (shows filename, size, date)
3. Click **📂 Load** to load the recording
4. Status changes to **📼 PLAYBACK** mode

#### Playing Back
- **▶️ Play**: Start automatic playback
- **⏸️ Pause**: Pause playback
- **⏹️ Stop**: Exit playback mode and return to LIVE
- **🐢 Slower / 🐇 Faster**: Change playback speed (0.25x, 0.5x, 1x, 2x, 4x, 8x)
- **Timeline Slider**: Scrub through the recording manually

#### What You See
All data updates in real-time during playback:
- ✅ Lane visualization (detected lanes + planned path)
- ✅ Lead car position and movement
- ✅ All telemetry (speed, steering, alerts, driver monitoring, etc.)
- ✅ Device health, GPS, calibration status
- ✅ Exact same view as live monitoring

### 3. API Endpoints

- **GET /api/logs**: List all log files (JSON array)
  ```json
  [
    {
      "filename": "drive_20260124_143022.jsonl",
      "size": 524288,
      "modified": 1737734022.5
    }
  ]
  ```

- **GET /api/log/<filename>**: Download specific log file (JSONL format)
  ```
  {"timestamp": 1737734022.5, "data": {...}}
  {"timestamp": 1737734022.6, "data": {...}}
  ...
  ```

## File Format

Logs are saved in **JSON Lines** format (`.jsonl`):
- One JSON object per line
- Each line contains: `{"timestamp": <float>, "data": <all_telemetry>}`
- Easy to parse and process with standard tools
- Can be analyzed with Python, jq, etc.

## Use Cases

### Debugging Issues
1. Drive with issue occurring
2. Stop server (logs auto-save)
3. Replay to see exactly what happened frame-by-frame
4. Scrub timeline to find the problematic moment

### Analyzing Performance
- Compare different drives on same route
- Review lane detection accuracy
- Check lead car tracking behavior
- Verify calibration over time

### Sharing Data
- Export log files from `/data/web_monitor_logs/`
- Share with others for analysis
- Load on any device running web_monitor_server.py

## Storage Management

### Disk Usage
- ~5-10 KB per second of driving
- ~300-600 KB per minute
- ~18-36 MB per hour
- For 8 hour driving day: ~144-288 MB

### Cleanup
```bash
# On KA2
cd /data/web_monitor_logs
ls -lh                    # View all logs
rm drive_20260120_*.jsonl  # Delete specific date
find . -mtime +7 -delete   # Delete logs older than 7 days
```

### Disable Logging
If you don't want logging, edit `web_monitor_server.py`:
```python
collector = DataCollector(enable_logging=False)
```

## Example Session

1. **Start server on KA2**:
   ```bash
   cd /data/openpilot/tools
   python3 web_monitor_server.py
   ```
   Output:
   ```
   📝 Logging to: /data/web_monitor_logs/drive_20260124_143022.jsonl
   ✅ Server started successfully!
   ```

2. **Drive your car** (monitor appears normal)

3. **Stop server** (Ctrl+C):
   ```
   ✅ Log saved: /data/web_monitor_logs/drive_20260124_143022.jsonl
   ```

4. **Replay later**:
   - Start server again
   - Open browser: `http://<KA2_IP>:8080`
   - Click **🔄 Refresh Logs**
   - Select your drive
   - Click **📂 Load**
   - Click **▶️ Play**
   - Watch your drive replay with full telemetry!

## Technical Details

### Log Structure
```json
{
  "timestamp": 1737734022.523,
  "data": {
    "vEgoCluster": 15.2,
    "enabled": true,
    "steeringAngleDeg": -2.5,
    "leadOne": {"distance": 45.3, "relVel": -1.2},
    "detectedLanes": [...],
    "path": [...],
    // ... all 69 telemetry fields
  }
}
```

### Performance
- **Logging**: Non-blocking, buffered writes every 5s
- **Playback**: Smooth at all speeds (0.25x - 8x)
- **Timeline**: Instant seek to any frame
- **Memory**: Entire log loaded in RAM (acceptable for 1-2 hour drives)

## Tips

- 🔄 Refresh log list after each drive
- 🐢 Use slow playback (0.25x-0.5x) to debug specific events
- 🐇 Use fast playback (4x-8x) to quickly find interesting moments
- ⏸️ Pause and use timeline slider for frame-by-frame analysis
- ⏹️ Stop playback to return to live monitoring immediately
