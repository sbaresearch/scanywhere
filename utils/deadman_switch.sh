#!/bin/bash
echo "Wireguard deadman switch started"

# turn off if inactive for 5 min
time_max_inactive=300

while true; do
    # time_uptime=$(printf %.0f $(awk '{print $1}' /proc/uptime))
    time_uptime=$(cat /proc/stat | grep btime | awk '{print $2}')
    time_wg_active=$(wg show all latest-handshakes | awk '{print $NF}' | sort | tail -n 1)
    time_limit=$(date +%s)
    time_limit=$((time_limit - time_max_inactive))

    # if last active client or reboot > time_max_inactive
    if ([ "$time_wg_active" -lt "$time_limit" ] && [ "$time_uptime" -lt "$time_limit" ]); then
        echo "time limit exceeded --> shutdown";
        shutdown -P now
    else
        echo "everything is good, sleep 60 sec";
    fi
    sleep 60
done
