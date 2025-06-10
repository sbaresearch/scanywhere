TOR_UID=$(id -u tor)
TRANS_PORT=9051
DNS_PORT=9053

# Flush rules
iptables -F
iptables -t nat -F
ip6tables -F
ip6tables -t nat -F

# Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT
ip6tables -A OUTPUT -o lo -j ACCEPT

# Don't redirect Tor's own traffic
iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
ip6tables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN

# Redirect DNS to Tor
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports $DNS_PORT
ip6tables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports $DNS_PORT

# Redirect TCP to Tor
iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT
ip6tables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

# Redirect UDP to Tor (optional – only if you really want it; Tor doesn’t fully support UDP)
iptables -t nat -A OUTPUT -p udp -j REDIRECT --to-ports $TRANS_PORT
ip6tables -t nat -A OUTPUT -p udp -j REDIRECT --to-ports $TRANS_PORT

# Allow Tor process traffic
iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
ip6tables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT

# Allow redirected TCP/UDP/DNS to reach Tor listener on localhost
iptables -A OUTPUT -p tcp -d 127.0.0.1 --dport $TRANS_PORT -j ACCEPT
iptables -A OUTPUT -p udp -d 127.0.0.1 --dport $TRANS_PORT -j ACCEPT
iptables -A OUTPUT -p udp -d 127.0.0.1 --dport $DNS_PORT -j ACCEPT

ip6tables -A OUTPUT -p tcp -d ::1 --dport $TRANS_PORT -j ACCEPT
ip6tables -A OUTPUT -p udp -d ::1 --dport $TRANS_PORT -j ACCEPT
ip6tables -A OUTPUT -p udp -d ::1 --dport $DNS_PORT -j ACCEPT

# Allow established/related
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
ip6tables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Drop everything else
iptables -A OUTPUT -j DROP
ip6tables -A OUTPUT -j DROP
