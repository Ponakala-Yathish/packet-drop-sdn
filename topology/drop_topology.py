from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class StarTopology(Topo):
    def build(self):
        # Create a single switch
        switch = self.addSwitch('s1', cls=OVSSwitch, protocols='OpenFlow13')

        # Create four hosts and link them to the switch
        for i in range(1, 5):
            host = self.addHost(f'h{i}', ip=f'10.0.0.{i}')
            self.addLink(host, switch)

def run():
    topo = StarTopology()
    # Connect to the Ryu controller you just set up
    net = Mininet(topo=topo, 
                  controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
                  switch=OVSSwitch,
                  link=TCLink)
    
    net.start()
    print("*** Topology is up. Type 'exit' to stop.")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
