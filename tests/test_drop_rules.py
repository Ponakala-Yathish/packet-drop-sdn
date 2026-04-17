import unittest
import subprocess
import time
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel

setLogLevel('warning')  # keep output clean during tests

class StarTopology(Topo):
    def build(self):
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        for i in range(1, 5):
            h = self.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
            self.addLink(h, s1)

class TestPacketDrop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Start Mininet once for all tests."""
        topo = StarTopology()
        cls.net = Mininet(
            topo=topo,
            controller=lambda name: RemoteController(
                name, ip='127.0.0.1', port=6633
            ),
            switch=OVSSwitch,
            link=TCLink
        )
        cls.net.start()
        time.sleep(3)  # wait for controller to push flow rules

    @classmethod
    def tearDownClass(cls):
        cls.net.stop()

    # ── T01: Drop rule exists in flow table at priority 200 ────────────────
    def test_T01_drop_rule_confirmed(self):
        result = subprocess.run(
            ['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'],
            capture_output=True, text=True
        )
        self.assertIn('priority=200', result.stdout,
                      "No priority-200 drop rule found in flow table")

    # ── T02: ICMP h1 -> h2 is BLOCKED (100% loss) ─────────────────────────
    def test_T02_icmp_h1_h2_blocked(self):
        h1 = self.net.get('h1')
        result = h1.cmd('ping -c 4 -W 1 10.0.0.2')
        # ping returns "X received" — must be 0
        self.assertIn('0 received', result,
                      f"Expected 0 received (blocked), got:\n{result}")

    # ── T03: ICMP h1 -> h3 is ALLOWED (0% loss) ───────────────────────────
    def test_T03_icmp_h1_h3_allowed(self):
        h1 = self.net.get('h1')
        result = h1.cmd('ping -c 4 -W 1 10.0.0.3')
        self.assertNotIn('0 received', result,
                         f"Expected replies (allowed), got:\n{result}")
        self.assertIn('4 received', result,
                      f"Expected 4 received, got:\n{result}")

    # ── T04: UDP port 5001 h3 -> h4 is BLOCKED ────────────────────────────
    def test_T04_udp_port_blocked(self):
        h3 = self.net.get('h3')
        h4 = self.net.get('h4')
        # Start iperf3 server on h4
        h4.cmd('iperf3 -s -p 5001 -D')
        time.sleep(1)
        # Send UDP from h3 to h4 port 5001 for 3 seconds
        result = h3.cmd('iperf3 -c 10.0.0.4 -u -p 5001 -t 3 -b 1M 2>&1')
        h4.cmd('pkill iperf3')
        # 100% packet loss means the drop rule is working
        self.assertIn('100%', result,
                      f"Expected 100% loss (UDP blocked), got:\n{result}")

    # ── T05: TCP h3 -> h4 is ALLOWED (no drop rule for TCP) ───────────────
    def test_T05_tcp_h3_h4_allowed(self):
        h3 = self.net.get('h3')
        h4 = self.net.get('h4')
        h4.cmd('iperf3 -s -D')
        time.sleep(1)
        result = h3.cmd('iperf3 -c 10.0.0.4 -t 3 2>&1')
        h4.cmd('pkill iperf3')
        # Should complete successfully (no "error" or "connection refused")
        self.assertNotIn('error', result.lower(),
                         f"TCP should be allowed, got:\n{result}")
        self.assertIn('sender', result,
                      f"Expected iperf3 sender summary, got:\n{result}")

    # ── T06: Drop rule survives (regression check via flow table) ──────────
    def test_T06_drop_rule_persists(self):
        """Re-check flow table to confirm drop rule still there mid-session."""
        result = subprocess.run(
            ['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'],
            capture_output=True, text=True
        )
        drop_lines = [l for l in result.stdout.splitlines()
                      if 'priority=200' in l and 'actions=drop' in l]
        self.assertGreaterEqual(len(drop_lines), 2,
                                f"Expected 2 drop rules, found: {drop_lines}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
