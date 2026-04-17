from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, udp

class PacketDropController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PacketDropController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # --- DROP RULE 1 ---
        # Block ALL IPv4 traffic from h1 (10.0.0.1) -> h2 (10.0.0.2)
        # Priority 200 > forwarding rules (priority 1), so this wins
        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1",
            ipv4_dst="10.0.0.2"
        )
        self.add_flow(datapath, 200, match, [])  # empty actions = DROP
        self.logger.info("CRITICAL: Drop rule installed for 10.0.0.1 -> 10.0.0.2")

        # --- DROP RULE 2 ---
        # Block UDP port 5001 from h3 (10.0.0.3) -> h4 (10.0.0.4)
        # ip_proto=17 means UDP; udp_dst=5001 matches iperf default port
        match = parser.OFPMatch(
            eth_type=0x0800,
            ip_proto=17,
            ipv4_src="10.0.0.3",
            ipv4_dst="10.0.0.4",
            udp_dst=5001
        )
        self.add_flow(datapath, 200, match, [])  # empty actions = DROP
        self.logger.info("CRITICAL: Drop rule installed for 10.0.0.3 -> 10.0.0.4 UDP port 5001")

        # --- TABLE-MISS RULE ---
        # Priority 0: anything not matched above goes to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn source MAC -> port mapping
        self.mac_to_port[dpid][src] = in_port

        # Decide output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install forwarding flow at priority 1 (lower than drop rules)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)
