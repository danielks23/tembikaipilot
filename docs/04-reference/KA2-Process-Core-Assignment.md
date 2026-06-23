# KA2 Process Core Assignment & CPU Usage

## CPU Architecture
The KA2 (RK3588) has 8 CPU cores:
- **A55 cluster (Cores 0-3)**: 1.8 GHz (Efficiency cores)
- **A76 cluster (Cores 4-7)**: 2.4 GHz (Performance cores)

## CPU Governor & Power States
| State | Governor | Cores 5-7 | Frequency |
|---|---|---|---|
| **Offroad** | `ondemand` | Offlined by `rkaiq_3A_server` | Scales dynamically (min ~408MHz) |
| **Onroad** | `performance` | Onlined | Locked at max (A55: 1.8GHz, A76: 2.352GHz) |

*Note: `schedutil` was tested on A55 but showed no meaningful power savings under sustained onroad load.*

## Process CPU Affinity
Processes set their core affinity via `config_realtime_process()` in `common/realtime.py`.

| Process | Pinned Core(s) | Cluster | Role |
|---|---|---|---|
| `boardd` | 4 | A76 | CAN hardware interface (100Hz) |
| `controlsd` | 4 | A76 | Main control loop (100Hz) |
| `modeld` | 7 | A76 | Road NN inference |
| `dmonitoringmodeld` | 6 | A76 | Driver monitoring NN |
| `camerad` | 6 | A76 | Camera capture & preprocessing |
| `plannerd` | 5 | A76 | Path planning & MPC |
| `radard` | 5 | A76 | Radar fusion & tracking |
| `torqued` | 0-3 | A55 | Live torque estimation |
| `paramsd` | 0-3 | A55 | Live vehicle param estimation |
| `encoderd` | 3 | A55 | Camera encoding (H.264) |
| `loggerd` | 0-3 | A55 | Route data logging |
| `uploader` | 0-3 | A55 | Cloud data upload |

*Note: `controlsd` currently has a bug where it falls back to cores 0-7 instead of pinning to core 4.*

## Measured CPU Usage (Onroad, No Car)
Based on `/proc/stat` sampling with `ForceOnroad=1`:

| Core | Assigned Processes | Busy % | Notes |
|---|---|---|---|
| 0-2 | Background | 2-4% | Idle |
| 3 | `encoderd`, `loggerd` | **13.7%** | Heaviest A55 core |
| 4 | `boardd` | 1.9% | Light |
| 5 | `plannerd`, `radard` | 1.9% | Light (no car) |
| 6 | `modeld`, `camerad`, `dmonitoringmodeld` | **11.9%** | Heaviest A76 core |
| 7 | `controlsd` | 1.7% | Light (no car) |

*Real driving with a car connected will significantly increase load on cores 4, 5, and 7.*

## Suggested Core Rebalancing
Current assignment leaves core 6 overloaded and cores 5/7 underutilized.
Proposed changes to `common/realtime.py` and process configs:

| Core | Proposed Assignment | Rationale |
|---|---|---|
| **4** | `boardd` + `controlsd` | Fixes controlsd bug, keeps 100Hz CAN↔control loop tight |
| **5** | `modeld` | Heaviest process, deserves dedicated A76 core |
| **6** | `camerad` + `dmonitoringmodeld` | Camera pipeline can share one core |
| **7** | `plannerd` | MPC solver needs A76 latency |
| **0-3** | `radard`, `torqued`, `paramsd`, loggers | Radar is lightweight CAN parsing, doesn't need A76 |

This balances A76 load to ~10-12% per core instead of concentrating 12% on core 6.
