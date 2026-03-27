# from scapy.all import *

# target = "192.168.1.10"   # fake target
# attacker = "192.168.1.50" # fake attacker

# packets = []

# # -------- PORT SCAN ATTACK --------
# for port in range(20, 40):  # small scan
#     pkt = IP(src=attacker, dst=target)/TCP(dport=port, flags="S")
#     packets.append(pkt)

# # -------- SMALL DDOS BURST --------
# for i in range(50):
#     pkt = IP(src=attacker, dst=target)/TCP(dport=80, flags="S")
#     packets.append(pkt)

# # save pcap
# wrpcap("tiny_attack.pcap", packets)

# print("tiny_attack.pcap generated")
from scapy.all import *

client = "192.168.1.10"
server = "192.168.1.1"

packets = []

sport = 12345

# -------- 1 Realistic TCP Handshake --------
syn = IP(src=client, dst=server)/TCP(sport=sport, dport=80, flags="S", seq=1000)
synack = IP(src=server, dst=client)/TCP(sport=80, dport=sport, flags="SA", seq=2000, ack=1001)
ack = IP(src=client, dst=server)/TCP(sport=sport, dport=80, flags="A", seq=1001, ack=2001)

packets += [syn, synack, ack]

# -------- Real HTTP Session --------
for i in range(50):
    data = IP(src=client, dst=server)/TCP(sport=sport, dport=80, flags="PA", seq=1001+i*10, ack=2001)/Raw(load="GET /index.html HTTP/1.1\r\n")
    packets.append(data)

# -------- Server Response --------
for i in range(50):
    resp = IP(src=server, dst=client)/TCP(sport=80, dport=sport, flags="PA", seq=2001+i*20, ack=1001)/Raw(load="HTTP/1.1 200 OK\r\n")
    packets.append(resp)

wrpcap("true_clean_normal.pcap", packets)

print("true_clean_normal.pcap generated")