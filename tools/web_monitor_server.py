#!/usr/bin/env python3
"""
Web Monitor Server - HTTP/WebSocket based (no BLE)
Access from phone browser at http://<KA2_IP>:8080
"""
import json
import time
import threading
import os
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import cereal.messaging as messaging
from openpilot.common.params import Params

PORT = 8080
UPDATE_HZ = 10  # Update rate for data

class DataCollector:
    """Collects openpilot data and serves via HTTP"""
    def __init__(self, enable_logging=True):
        self.sm = messaging.SubMaster([
            'modelV2', 'controlsState', 'radarState', 'liveCalibration',
            'driverMonitoringState', 'carState', 'longitudinalPlan',
            'deviceState', 'gpsLocationExternal', 'pandaStates', 'lateralPlan',
            'carControl',
        ])
        self.params = Params()
        self.latest_data = {}
        self.running = True

        # Logging setup
        self.enable_logging = enable_logging
        self.log_dir = Path('/data/web_monitor_logs') if os.path.exists('/data') else Path('./web_monitor_logs')
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = None
        self.log_buffer = []
        self.last_flush = time.time()

        if self.enable_logging:
            log_filename = f"drive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            self.current_log_file = self.log_dir / log_filename
            print(f"📝 Logging to: {self.current_log_file}")

        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _update_loop(self):
        """Continuously collect data"""
        while self.running:
            self.sm.update(100)  # 100ms timeout

            # Control State
            cs = self.sm['controlsState']
            data = {
                'timestamp': time.time(),
                'state': str(cs.state),
                'enabled': cs.enabled,
                'engageable': cs.engageable,
                'active': cs.active,
                'experimentalMode': cs.experimentalMode,
                'vCruiseCluster': float(cs.vCruiseCluster),
                'alertText1': cs.alertText1,
                'alertText2': cs.alertText2,
                'alertStatus': str(cs.alertStatus),
                'alertSize': str(cs.alertSize),
                'longControlState': str(cs.longControlState),
                'canErrorCounter': cs.canErrorCounter,
            }

            # Car State
            car = self.sm['carState']
            data.update({
                'vEgo': float(car.vEgo),
                'vEgoCluster': float(car.vEgoCluster),
                'gas': float(car.gas),
                'brake': float(car.brake),
                'steeringAngleDeg': float(car.steeringAngleDeg),
                'steeringTorque': float(car.steeringTorque),
                'steeringPressed': car.steeringPressed,
                'gasPressed': car.gasPressed,
                'brakePressed': car.brakePressed,
                'gearShifter': str(car.gearShifter),
                'standstill': car.standstill,
                'leftBlinker': car.leftBlinker,
                'rightBlinker': car.rightBlinker,
            })

            # Lead Car
            radar = self.sm['radarState']
            if radar.leadOne.status:
                data['leadOne'] = {
                    'distance': float(radar.leadOne.dRel),
                    'velocity': float(radar.leadOne.vRel),
                    'lateral': float(radar.leadOne.yRel),
                }

            # Driver Monitoring
            dm = self.sm['driverMonitoringState']
            data.update({
                'dmActive': dm.isActiveMode,
                'faceDetected': dm.faceDetected,
                'isDistracted': dm.isDistracted,
                'awarenessStatus': float(dm.awarenessStatus),
            })

            # Longitudinal
            plan = self.sm['longitudinalPlan']
            data.update({
                'personality': int(plan.personality),
                'hasLead': plan.hasLead,
                'fcw': plan.fcw,
            })

            # Device/Thermal Status
            device = self.sm['deviceState']
            data.update({
                'cpuTemp': float(max(device.cpuTempC)) if device.cpuTempC else 0,
                'memoryUsage': int(device.memoryUsagePercent),
                'batteryPercent': int(device.batteryPercent),
                'batteryStatus': str(device.batteryStatus),
                'freeSpace': float(device.freeSpacePercent),
            })

            # GPS Data
            gps = self.sm['gpsLocationExternal']
            if gps.flags & 1:  # Has valid fix
                data.update({
                    'gpsSpeed': float(gps.speed),
                    'gpsAccuracy': float(gps.accuracy),
                    'gpsAltitude': float(gps.altitude),
                    'gpsBearing': float(gps.bearingDeg),
                    'gpsLatitude': float(gps.latitude),
                    'gpsLongitude': float(gps.longitude),
                })

            # Model Confidence
            model = self.sm['modelV2']
            if len(model.laneLineProbs) >= 4:
                data.update({
                    'laneConfidenceLL': float(model.laneLineProbs[0]),
                    'laneConfidenceL': float(model.laneLineProbs[1]),
                    'laneConfidenceR': float(model.laneLineProbs[2]),
                    'laneConfidenceRR': float(model.laneLineProbs[3]),
                })
            data['modelExecutionTime'] = float(model.modelExecutionTime) if model.modelExecutionTime else 0

            # Path data for visualization
            if len(model.position.x) > 0:
                path = []
                for i in range(min(len(model.position.x), 33)):
                    if i < len(model.position.y):
                        path.append({
                            'x': float(model.position.x[i]),
                            'y': float(model.position.y[i])
                        })
                data['path'] = path

            # Lane lines detected by the model (what openpilot actually sees)
            if len(model.laneLines) >= 4:
                lanes = []
                for lane_idx in range(4):  # 0=far left, 1=left, 2=right, 3=far right
                    lane = model.laneLines[lane_idx]
                    if len(lane.x) > 0:
                        lane_points = []
                        for i in range(min(len(lane.x), len(lane.y))):
                            lane_points.append({
                                'x': float(lane.x[i]),
                                'y': float(lane.y[i])
                            })
                        lanes.append(lane_points)
                    else:
                        lanes.append([])
                data['detectedLanes'] = lanes

            # Panda/CAN Health
            pandas = self.sm['pandaStates']
            if len(pandas) > 0:
                panda = pandas[0]
                data.update({
                    'pandaVoltage': int(panda.voltage),
                    'pandaCurrent': int(panda.current),
                    'pandaSafetyMode': str(panda.safetyModel),
                    'canRxErrors': int(panda.canRxErrs),
                    'canTxErrors': int(panda.canTxErrs),
                })

            # Lateral Planning
            lat = self.sm['lateralPlan']
            data.update({
                'desiredCurvature': float(lat.curvatures[0]) if len(lat.curvatures) > 0 else 0,
                'lateralAccel': float(lat.accels[0]) if len(lat.accels) > 0 else 0,
            })

            # Control Actuators
            ctrl = self.sm['carControl']
            data.update({
                'desiredSteeringAngle': float(ctrl.actuators.steeringAngleDeg),
                'desiredAccel': float(ctrl.actuators.accel),
            })

            # Calibration
            cal = self.sm['liveCalibration']
            rpy = cal.rpyCalib if len(cal.rpyCalib) >= 3 else [0, 0, 0]
            data.update({
                'calRoll': float(rpy[0]),
                'calPitch': float(rpy[1]),
                'calYaw': float(rpy[2]),
                'calStatus': int(cal.calStatus),
            })

            # System Info
            data.update({
                'dongleId': self.params.get("DongleId", encoding='utf-8'),
                'isMetric': self.params.get_bool("IsMetric"),
                'isOffroad': self.params.get_bool("IsOffroad"),
            })

            self.latest_data = data

            # Log data if enabled
            if self.enable_logging and self.current_log_file:
                self.log_buffer.append({'timestamp': time.time(), 'data': data})

                # Flush every 5 seconds or 50 entries
                if time.time() - self.last_flush > 5 or len(self.log_buffer) >= 50:
                    self._flush_log()

            time.sleep(1.0 / UPDATE_HZ)

    def get_data(self):
        """Get latest collected data"""
        return self.latest_data

    def stop(self):
        self.running = False

class WebMonitorHandler(SimpleHTTPRequestHandler):
    collector = None

    def do_GET(self):
        if self.path == '/api/data':
            # Serve JSON data
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = self.collector.get_data() if self.collector else {}
            self.wfile.write(json.dumps(data).encode())

        elif self.path == '/api/logs':
            # List available log files
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            log_files = []
            if self.collector and self.collector.log_dir.exists():
                for log_file in sorted(self.collector.log_dir.glob('*.jsonl'), reverse=True):
                    log_files.append({
                        'filename': log_file.name,
                        'size': log_file.stat().st_size,
                        'modified': log_file.stat().st_mtime
                    })
            self.wfile.write(json.dumps(log_files).encode())

        elif self.path.startswith('/api/log/'):
            # Serve specific log file
            log_filename = self.path.split('/api/log/')[1]
            if self.collector:
                log_path = self.collector.log_dir / log_filename
                if log_path.exists() and log_path.suffix == '.jsonl':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    with open(log_path, 'r') as f:
                        self.wfile.write(f.read().encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Log file not found')
            else:
                self.send_response(404)
                self.end_headers()

        elif self.path == '/' or self.path == '/index.html':
            # Serve main page
            self.path = '/monitor.html'
            return SimpleHTTPRequestHandler.do_GET(self)
        else:
            return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {format % args}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    pass

def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def main():
    import os
    os.chdir(Path(__file__).parent)

    print("=" * 60)
    print("🌐 KA2 Web Monitor Server (HTTP)")
    print("=" * 60)

    # Start data collector with logging enabled
    collector = DataCollector(enable_logging=True)
    WebMonitorHandler.collector = collector

    local_ip = get_local_ip()

    with ThreadedHTTPServer(("", PORT), WebMonitorHandler) as httpd:
        print(f"\n✅ Server started successfully!")
        print(f"\n📱 Access from your phone:")
        print(f"   http://{local_ip}:{PORT}")
        print(f"\n💻 Or from PC:")
        print(f"   http://localhost:{PORT}")
        print(f"\n📊 API endpoints:")
        print(f"   http://{local_ip}:{PORT}/api/data  (live data)")
        print(f"   http://{local_ip}:{PORT}/api/logs  (log files)")
        print(f"\n📁 Log directory: {collector.log_dir}")
        print(f"\n🛑 Press Ctrl+C to stop server")
        print("=" * 60)
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Stopping server...")
            collector.stop()
            print("Server stopped")

if __name__ == "__main__":
    main()
