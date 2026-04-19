# Packet Drop Simulator — SDN Mininet Project

## Problem Statement
This project implements an SDN-based packet drop simulator using Mininet
and a Ryu OpenFlow controller. The controller installs high-priority
**drop rules** that silently discard specific network flows, while all
other traffic continues to forward normally through a learning switch.

**What gets dropped:**
- ALL traffic from h1 (10.0.0.1) → h2 (10.0.0.2)
- UDP port 5001 from h3 (10.0.0.3) → h4 (10.0.0.4)

**What is allowed:**
- h1 → h3, h1 → h4, h3 → h4 (TCP), and all other pairs

---

## Network Topology
h1 (10.0.0.1)      h2 (10.0.0.2)
\                /
\              /
[ s1 (OVS) ] ←→ Ryu Controller (127.0.0.1:6633)
/              
/                
h3 (10.0.0.3)      h4 (10.0.0.4)

Single switch, 4 hosts, OpenFlow 1.3, RemoteController.

---

## Flow Rule Design

| Priority | Match | Action | Purpose |
|----------|-------|--------|---------|
| 200 | IPv4 src=10.0.0.1 dst=10.0.0.2 | DROP | Block h1→h2 |
| 200 | IPv4 UDP src=10.0.0.3 dst=10.0.0.4 port=5001 | DROP | Block h3→h4 UDP |
| 1 | src/dst MAC | output(port) | Normal forwarding |
| 0 | * (anything) | → Controller | Table-miss |

Drop rules have **higher priority than forwarding rules**, so they always win.

---

## Setup

```bash
# Install dependencies
sudo apt install mininet openvswitch-switch iperf3 tshark -y
pip3 install ryu
```

---

## Execution

```bash
# Terminal 1 — Start Ryu controller
cd controller
ryu-manager packet_drop_controller.py

# Terminal 2 — Launch Mininet topology
cd topology
sudo python3 drop_topology.py
```

---

## Test Scenarios

### Scenario A — Blocked vs Allowed (ICMP / ping)
```bash
mininet> h1 ping -c 4 h2    # BLOCKED → 100% packet loss
mininet> h1 ping -c 4 h3    # ALLOWED → 0% packet loss
```

### Scenario B — UDP Blocked, TCP Allowed (iperf3)
```bash
# UDP blocked
mininet> h4 iperf3 -s -p 5001 &
mininet> h3 iperf3 -c 10.0.0.4 -u -p 5001 -t 5   # 100% loss

# TCP allowed
mininet> h4 iperf3 -s &
mininet> h3 iperf3 -c 10.0.0.4 -t 5               # ~40 Gbps passes
```

### Scenario C — Wireshark/tshark Proof
```bash
# h2 listens — should see ZERO packets (blocked)
mininet> h2 tshark -i h2-eth0 -c 20 &
mininet> h1 ping -c 5 h2

# h3 listens — should see packets (allowed)
mininet> h3 tshark -i h3-eth0 -c 20 &
mininet> h1 ping -c 5 h3
```

### Scenario D — Flow Table Dump
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
# priority=200 → drop rules (actions=drop)
# priority=1   → forwarding rules
# priority=0   → table-miss → controller
```

---

## Regression Tests

```bash
# Make sure controller is running in Terminal 1 first
sudo PYTHONPATH=. python3 tests/test_drop_rules.py
```

Expected output:
T01: Drop rule confirmed ... ok
T02: ICMP h1->h2 blocked ... ok
T03: ICMP h1->h3 allowed ... ok
T04: UDP port 5001 blocked ... ok
T05: TCP h3->h4 allowed ... ok
T06: Drop rule persists ... ok
Ran 6 tests in XX.XXXs
OK

---

## Screenshots

| What | Result |
|------|--------|
| `h1 ping h2` | 100% packet loss |
| `h1 ping h3` | 0% packet loss |
| tshark on h2 (blocked) | 0 packets captured |
| tshark on h3 (allowed) | ICMP packets visible |
| ovs-ofctl dump-flows | priority=200 drop rules |
| iperf3 UDP blocked | 100% loss |
| iperf3 TCP allowed | ~40 Gbps |
| All tests passing | T01–T06 OK |

*(Screenshots in `/screenshots` folder)*

---
