#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/net/ipv4/tcp_input.c","tcp_cong_control"),
("kernel/net/ipv4/tcp_input.c","tcp_ack"),
("kernel/net/core/dev.c","netif_receive_skb"),
("kernel/drivers/base/power/wakeup.c","wakeup_source"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
print("PASS: TCP/IP receive, congestion-control and wakeup-source audit anchors.")
