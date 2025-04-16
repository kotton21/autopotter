#  - Contents of /proc/<pid>/status and /proc/<pid>/environ
#  - A list of open files via lsof
#
# Adjust the CPU threshold (20%) or sleep interval (2 seconds) as needed.

# Set a high column width to minimize truncation in ps and top output.
export COLUMNS=500

while true; do
    # Run top in batch mode with one iteration.
    # Pipe the output to awk to filter lines:
    #   - only lines starting with a numeric PID (filtering out header lines)
    #   - those where the 9th column (%CPU) is greater than 20.
    top -b -n1 | awk '($1 ~ /^[0-9]+$/ && $9+0 > 20) { print $0 }' | while read -r line; do
        # Extract the PID from the first column.
        pid=$(echo "$line" | awk '{print $1}')
        cpu=$(echo "$line" | awk '{print $9}')
        
        echo "Timestamp: $(date)" >> ~/cpu_usage.log
        echo "=== top output: $line" >> ~/cpu_usage.log
        
        echo "=== Process Details (ps extended) ===" >> ~/cpu_usage.log
        ps -p $pid -o pid,ppid,user,start_time,etimes,cmd,%cpu,%mem -ww >> ~/cpu_usage.log
        
        echo "=== /proc/$pid/status ===" >> ~/cpu_usage.log
        cat /proc/$pid/status >> ~/cpu_usage.log
        
        echo "=== /proc/$pid/environ ===" >> ~/cpu_usage.log
        tr '\0' '\n' < /proc/$pid/environ >> ~/cpu_usage.log
        
        echo "=== Open Files (lsof) ===" >> ~/cpu_usage.log
        lsof -p $pid >> ~/cpu_usage.log
        
        echo "-------------------------------------" >> ~/cpu_usage.log
    done
    sleep 2
done