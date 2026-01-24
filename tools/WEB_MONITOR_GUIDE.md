# Web Monitor Guide (HTTP Method)

## 📋 Overview

This web monitor uses **HTTP polling** instead of Bluetooth:
- ✅ **No BLE pairing required** - Just open URL
- ✅ **Works on any device** - Phone, tablet, PC
- ✅ **Any browser** - Chrome, Safari, Firefox, Edge
- ✅ **Multiple clients** - Many devices can connect simultaneously
- ✅ **Faster setup** - No Bluetooth permissions needed

---

## 🚀 Quick Start

### Step 1: SSH into KA2
```bash
ssh comma@<KA2_IP_ADDRESS>
```

### Step 2: Start the server
```bash
cd /data/openpilot/tools
python3 web_monitor_server.py
```

You'll see:
```
============================================================
🌐 KA2 Web Monitor Server (HTTP)
============================================================

✅ Server started successfully!

📱 Access from your phone:
   http://192.168.1.100:8080

💻 Or from PC:
   http://localhost:8080

📊 API endpoint:
   http://192.168.1.100:8080/api/data

🛑 Press Ctrl+C to stop server
============================================================
```

### Step 3: Open on any device
1. **Connect device to same WiFi** as KA2
2. **Open any browser** (Chrome, Safari, Firefox, etc.)
3. **Go to the URL** shown above
4. **Done!** No pairing, no permissions, just works

---

## 📊 What You'll See

```
┌────────────────────────────┐
│  🚗 KA2 Web Monitor        │
│  Status: Connected         │
├────────────────────────────┤
│        85.5 km/h           │
│   Cruise: 90.0 km/h        │
├────────────────────────────┤
│  🎮 System State           │
│  State: enabled            │
│  Enabled: ✅ Yes           │
│  Engageable: ✅ Yes        │
│  Experimental: ⚪ Off      │
├────────────────────────────┤
│  ⚡ Control                │
│  Active: ✅ Yes            │
│  Long State: pid           │
│  CAN Errors: 0             │
│  Personality: Standard     │
├────────────────────────────┤
│  🚙 Car Inputs             │
│  Steering: -2.5°           │
│  Gas: 15% | Brake: 0%      │
│  Gear: drive               │
├────────────────────────────┤
│  🚙 Lead Car               │
│  Distance: 45.2m           │
│  Velocity: -2.1m/s         │
│  FCW: Off                  │
├────────────────────────────┤
│  👁️ Driver Monitoring      │
│  Face Detected: ✅         │
│  Distracted: ✅ No         │
│  Awareness: 98%            │
└────────────────────────────┘
```

---

## 🔧 Auto-Start on Boot

Make the server start automatically:

### Create systemd service
```bash
sudo nano /etc/systemd/system/web-monitor.service
```

Paste:
```ini
[Unit]
Description=Web Monitor Server
After=network.target

[Service]
Type=simple
User=comma
WorkingDirectory=/data/openpilot/tools
ExecStart=/usr/bin/python3 /data/openpilot/tools/web_monitor_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start
```bash
sudo systemctl enable web-monitor.service
sudo systemctl start web-monitor.service
sudo systemctl status web-monitor.service
```

Now it's always accessible!

---

## 📡 API Usage

You can also access raw data via API:

```bash
# Get current data as JSON
curl http://192.168.1.100:8080/api/data

# Pretty print
curl http://192.168.1.100:8080/api/data | python3 -m json.tool
```

Example response:
```json
{
  "timestamp": 1706099234.567,
  "state": "enabled",
  "enabled": true,
  "engageable": true,
  "vEgoCluster": 23.6,
  "alertText1": "",
  "canErrorCounter": 0,
  "gas": 0.12,
  "brake": 0.0,
  "steeringAngleDeg": -2.5,
  "leadOne": {
    "distance": 45.2,
    "velocity": -2.1
  }
}
```

---

## 💻 Multiple Devices

Unlike BLE, **multiple devices can connect simultaneously**:
- View on phone while driving
- Monitor on tablet in passenger seat
- Log data on laptop
- All at the same time!

---

## 🔍 Troubleshooting

### Can't access from phone

**Check KA2 IP:**
```bash
# On KA2
ip addr show wlan0 | grep "inet "
```

**Test locally:**
```bash
# On KA2
curl http://localhost:8080/api/data
```

**Check firewall:**
```bash
sudo iptables -L -n | grep 8080
```

### Server won't start

**Check if port is in use:**
```bash
sudo netstat -tulpn | grep 8080
```

**Use different port:**
Edit `web_monitor_server.py` and change `PORT = 8080` to `PORT = 8081`

### Data not updating

**Check SubMaster:**
```bash
# On KA2
tmux attach
# Verify openpilot processes are running
```

**Check logs:**
```bash
tail -f /data/community/crashes/swaglog | grep -i error
```

---

## 🎯 Comparison: HTTP vs BLE

| Feature | HTTP Method | BLE Method |
|---------|-------------|------------|
| Setup | ✅ Instant | ❌ Pairing required |
| Browser | ✅ Any browser | ❌ Chrome only |
| Devices | ✅ Multiple | ❌ One at a time |
| Permissions | ✅ None | ❌ Location/BLE |
| Range | ✅ WiFi range | ❌ 10m BLE range |
| Latency | ✅ ~100ms | ❌ ~200ms |
| iOS Support | ✅ Full | ❌ Limited |

**HTTP method is recommended for most users!**

---

## 📊 Update Rate

Default: **5 Hz** (200ms refresh)

To change, edit `monitor.html`:
```javascript
updateInterval = setInterval(fetchData, 100); // 10 Hz
```

Or edit `web_monitor_server.py`:
```python
UPDATE_HZ = 20  # 20 Hz data collection
```

---

## 🔐 Security

**No authentication by default** - Anyone on WiFi can access.

To add basic auth, install nginx as reverse proxy:
```bash
sudo apt-get install nginx apache2-utils
htpasswd -c /etc/nginx/.htpasswd admin
# Configure nginx to proxy to localhost:8080 with auth
```

---

## 💡 Advanced Usage

### Data Logging
```bash
# Log data to file
while true; do
  curl -s http://localhost:8080/api/data >> data.jsonl
  sleep 0.2
done
```

### Custom Dashboard
Edit `monitor.html` to customize:
- Add charts/graphs
- Change colors
- Add more metrics
- Create custom alerts

### Remote Access
```bash
# Use SSH tunnel for remote access
ssh -L 8080:localhost:8080 comma@<KA2_IP>
# Access on local machine: http://localhost:8080
```

---

## 🎉 Benefits

- **No BLE complexity** - Just HTTP
- **Works everywhere** - Any device, any browser
- **Easy to debug** - Standard web tools
- **Multiple viewers** - Share with passengers
- **API access** - Integrate with other tools
