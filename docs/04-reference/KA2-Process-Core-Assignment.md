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
Processes set their core affinity via `config_realtime_process()` in `common/realtime.py`. **Must be called before any blocking initialization** (e.g., `CarD`, `VisionIpcClient`) to ensure affinity is set before the process enters its main loop.

| Process | Pinned Core(s) | Cluster | Policy | Role |
|---|---|---|---|---|
| `boardd` | 4 | A76 | SCHED_FIFO/54 | CAN hardware interface (100Hz) |
| `controlsd` | 4 | A76 | SCHED_FIFO/53 | Main control loop (100Hz) |
| `modeld` | 7 | A76 | SCHED_FIFO/54 | Road NN inference |
| `dmonitoringmodeld` | 6 | A76 | SCHED_FIFO/56 | Driver monitoring NN |
| `camerad` | 6 | A76 | SCHED_FIFO/53 | Camera capture & preprocessing |
| `plannerd` | 5 | A76 | SCHED_FIFO/51 | Path planning & MPC |
| `radard` | 5 | A76 | SCHED_FIFO/51 | Radar fusion & tracking |
| `torqued` | 0-3 | A55 | SCHED_FIFO/5 | Live torque estimation |
| `paramsd` | 0-3 | A55 | SCHED_FIFO/5 | Live vehicle param estimation |
| `encoderd` | 3 | A55 | SCHED_FIFO/52 | Camera encoding (H.264) |
| `loggerd` | 0-3 | A55 | (default) | Route data logging |
| `uploader` | 0-3 | A55 | (default) | Cloud data upload |

## Verified Affinity (Live KA2)
Confirmed on KA2 (all processes show correct `SCHED_FIFO` policy and core mask):

| Process | Core Mask | Policy | Verified |
|---|---|---|---|
| `controlsd` | `10` (core 4) | SCHED_FIFO/53 | Yes |
| `boardd` | `10` (core 4) | SCHED_FIFO/54 | Yes |
| `plannerd` | `20` (core 5) | SCHED_FIFO/51 | Yes |
| `radard` | `20` (core 5) | SCHED_FIFO/51 | Yes |
| `modeld` | `80` (core 7) | SCHED_FIFO/54 | Yes |
| `dmonitoringmodeld` | `40` (core 6) | SCHED_FIFO/56 | Yes |
| `camerad` | `40` (core 6) | SCHED_FIFO/53 | Yes |
| `encoderd` | `8` (core 3) | SCHED_FIFO/52 | Yes |
| `torqued` | `f` (cores 0-3) | SCHED_FIFO/5 | Yes |
| `paramsd` | `f` (cores 0-3) | SCHED_FIFO/5 | Yes |

## Known Issues

### `rkaiq_3A_server` re-offlines cores 5-7 (~24 min cycle)
The closed-source Rockchip camera daemon periodically offlines cores 5-7, disrupting processes pinned to those cores (`plannerd`, `radard`, `dmonitoringmodeld`, `camerad`, `modeld`). No mitigation is currently implemented. See [KA2-Hardware-Reference](./KA2-Hardware-Reference.md#cpu-core-offlining) for options.

## Suggested Core Rebalancing
Current assignment leaves core 6 overloaded and cores 5/7 underutilized.
Proposed changes to `common/realtime.py` and process configs:

| Core | Proposed Assignment | Rationale |
|---|---|---|
| **4** | `boardd` + `controlsd` | Keeps 100Hz CAN↔control loop tight |
| **5** | `modeld` | Heaviest process, deserves dedicated A76 core |
| **6** | `camerad` + `dmonitoringmodeld` | Camera pipeline can share one core |
| **7** | `plannerd` | MPC solver needs A76 latency |
| **0-3** | `radard`, `torqued`, `paramsd`, loggers | Radar is lightweight CAN parsing, doesn't need A76 |

This balances A76 load to ~10-12% per core instead of concentrating 12% on core 6.
