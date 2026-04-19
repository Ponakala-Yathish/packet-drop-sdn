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
       +---------------------------------------+
       |            Ryu Controller             |
       |           (127.0.0.1:6633)            |
       +------------------+--------------------+
                          ^
                          | (OpenFlow)
                          v
       +------------------+--------------------+
       |          s1 (Open vSwitch)            |
       +--+-----------+-----------+---------+--+
          |           |           |         |
    +-----+--+    +---+----+    +-+------+  +-----+--+
    |   h1   |    |   h2   |    |   h3   |  |   h4   |
    |10.0.0.1|    |10.0.0.2|    |10.0.0.3|  |10.0.0.4|
    +--------+    +--------+    +--------+  +--------+

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

## Dependencies

```bash
# Install dependencies
sudo apt install mininet openvswitch-switch iperf3 tshark -y
pip3 install ryu
```

---

# Packet Drop SDN — Demo Walkthrough

## Setup & Running

### Terminal 1 — Start Controller

```bash
cd ~/packet-drop-sdn
source ryu_venv/bin/activate
cd controller
ryu-manager packet_drop_controller.py
```

> ✅ Wait until you see:
> ```
> CRITICAL: Drop rule installed for 10.0.0.1 -> 10.0.0.2
> CRITICAL: Drop rule installed for 10.0.0.3 -> 10.0.0.4 UDP port 5001
> ```
> Leave this terminal open. Never close it.

---

### Terminal 2 — Start Mininet

```bash
cd ~/packet-drop-sdn
source ryu_venv/bin/activate
cd topology
sudo python3 drop_topology.py
```

> ✅ Wait until you see the `mininet>` prompt.

---

## Screenshots

### Screenshot 1 — Ping Blocked (h1 → h2)

In Terminal 2:

```bash
mininet> h1 ping -c 4 h2
```

> ✅ You'll see `100% packet loss`. Take screenshot.

---

### Screenshot 2 — Ping Allowed (h1 → h3)

```bash
mininet> h1 ping -c 4 h3
```

> ✅ You'll see `0% packet loss`. Take screenshot.

---

### Screenshot 3 — tshark Blocked (h2 gets no ICMP)

```bash
mininet> h2 tshark -i h2-eth0 -c 10 -f "icmp" &
mininet> h1 ping -c 5 h2
```

> ✅ tshark prints nothing / only ARP. Ping shows 100% loss. Take screenshot.

---

### Screenshot 4 — tshark Allowed (h3 gets ICMP)

```bash
mininet> h3 tshark -i h3-eth0 -c 10 -f "icmp" &
mininet> h1 ping -c 5 h3
```

> ✅ tshark prints actual ICMP packets. Ping shows 0% loss. Take screenshot.

---

### Screenshot 5 — UDP Blocked (iperf)

```bash
mininet> h4 iperf -s -u -p 5001 &
mininet> h3 iperf -c 10.0.0.4 -u -p 5001 -b 1M -t 5
```

> ✅ You'll see `did not receive ack` warning. Take screenshot.

---

### Screenshot 6 — TCP Allowed (iperf)

```bash
mininet> h4 iperf -s &
mininet> h3 iperf -c 10.0.0.4 -t 5
```

> ✅ You'll see big bandwidth numbers like `40 Gbits/sec`. Take screenshot.

---

### Screenshot 7 — Flow Table Dump

In Terminal 3 (outside mininet):

```bash
cd ~/packet-drop-sdn
source ryu_venv/bin/activate
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

> ✅ You'll see `priority=200` lines with `actions=drop`. Take screenshot.

---

### Screenshot 8 — All Tests Passing

In Terminal 2, first exit mininet:

```bash
mininet> exit
```

Then in Terminal 3:

```bash
cd ~/packet-drop-sdn
source ryu_venv/bin/activate
sudo mn -c
sudo PYTHONPATH=. python3 tests/test_drop_rules.py
```

> ✅ Wait ~60 seconds. You'll see T01–T06 all `ok`. Take screenshot.

**Expected output:**

```
T01: Drop rule confirmed  ... ok
T02: ICMP h1->h2 blocked  ... ok
T03: ICMP h1->h3 allowed  ... ok
T04: UDP port 5001 blocked ... ok
T05: TCP h3->h4 allowed   ... ok
T06: Drop rule persists   ... ok

Ran 6 tests in XX.XXXs

OK

```

## Screenshots

| What | Result |
|------|--------|
| `h1 ping h2` | 100% packet loss |

<img width="1030" height="136" alt="image" src="https://github.com/user-attachments/assets/f0ff39f8-e3d5-4425-b237-080af1c15659" />


| `h1 ping h3` | 0% packet loss |

<img width="1004" height="192" alt="image" src="https://github.com/user-attachments/assets/1625bb22-7070-4ed6-9692-e5be0bcdb7e6" />

| tshark on h2 (blocked) | 0 packets captured |

<img width="1505" height="457" alt="image" src="https://github.com/user-attachments/assets/96666ca4-98c6-4619-8273-0422e282b9fa" />


| tshark on h3 (allowed) | ICMP packets visible |

<img width="743" height="226" alt="image" src="https://github.com/user-attachments/assets/fea17456-1fce-492e-bc0c-99e72187d3db" />

| ovs-ofctl dump-flows | priority=200 drop rules |

<img width="1498" height="171" alt="image" src="https://github.com/user-attachments/assets/ed7ec84e-98ee-40db-8994-35104606492d" />

| iperf3 UDP blocked | 100% loss |

<img width="918" height="241" alt="Screenshot 2026-04-19 192912" src="https://github.com/user-attachments/assets/a91ba112-beda-4699-816c-f8abd4bf5497" />


| iperf3 TCP allowed | ~40 Gbps |

<img width="728" height="261" alt="image" src="https://github.com/user-attachments/assets/e27f36af-f2c8-42cb-81fe-2ee73ebdc7fe" />

| All tests passing | T01–T06 OK |


<img width="1245" height="236" alt="image" src="https://github.com/user-attachments/assets/26a3d34d-7965-4afc-9842-1b75b174c584" />


---

## References
1. Ryu SDN Framework — https://ryu.readthedocs.io
2. Mininet Walkthrough — http://mininet.org/walkthrough/
3. OpenFlow Specification v1.3 — https://opennetworking.org
4. Open vSwitch ovs-ofctl docs — https://www.openvswitch.org
5. Feamster et al., "The Road to SDN", ACM Queue 2014
