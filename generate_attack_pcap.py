from scapy.all import *

target = "192.168.1.10"   # fake target
attacker = "192.168.1.50" # fake attacker

packets = []

# -------- PORT SCAN ATTACK --------
for port in range(20, 40):  # small scan
    pkt = IP(src=attacker, dst=target)/TCP(dport=port, flags="S")
    packets.append(pkt)

# -------- SMALL DDOS BURST --------
for i in range(50):
    pkt = IP(src=attacker, dst=target)/TCP(dport=80, flags="S")
    packets.append(pkt)

# save pcap
wrpcap("tiny_attack.pcap", packets)

print("tiny_attack.pcap generated")
