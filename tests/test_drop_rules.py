import unittest
import subprocess
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from topology.drop_topology import StarTopology

class TestPacketDrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net = Mininet(topo=StarTopology(), 
                          controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
                          switch=OVSSwitch, link=TCLink)
        cls.net.start()
        time.sleep(5) # Wait for Ryu connection

    @classmethod
    def tearDownClass(cls):
        cls.net.stop()

    def test_T01_drop_rule_installed(self):
        output = subprocess.check_output(['sudo', 'ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'])
        self.assertIn(b'actions=drop', output)
        print("[PASS] T01: Drop rule confirmed")

    def test_T02_icmp_h1_h2_blocked(self):
        res = self.net.get('h1').cmd('ping -c 3 10.0.0.2')
        self.assertIn('100% packet loss', res)
        print("[PASS] T02: ICMP h1->h2 blocked")

    def test_T03_icmp_h1_h3_allowed(self):
        res = self.net.get('h1').cmd('ping -c 3 10.0.0.3')
        self.assertIn('0% packet loss', res)
        print("[PASS] T03: ICMP h1->h3 allowed")

    def test_T04_udp_port_blocked(self):
        # Testing the UDP drop rule on port 5001
        h4 = self.net.get('h4')
        h3 = self.net.get('h3')
        h4.cmd('iperf3 -s -p 5001 &')
        res = h3.cmd('iperf3 -u -c 10.0.0.4 -p 5001 -t 2')
        self.assertIn('0/0', res) # iperf3 UDP receiver stats will be empty
        h4.cmd('pkill iperf3')
        print("[PASS] T04: UDP port 5001 blocked")

    def test_T05_tcp_h3_h4_allowed(self):
        h4 = self.net.get('h4')
        h3 = self.net.get('h3')
        h4.cmd('iperf3 -s &')
        res = h3.cmd('iperf3 -c 10.0.0.4 -t 2')
        self.assertIn('receiver', res)
        h4.cmd('pkill iperf3')
        print("[PASS] T05: TCP h3->h4 allowed")

if __name__ == '__main__':
    unittest.main()
