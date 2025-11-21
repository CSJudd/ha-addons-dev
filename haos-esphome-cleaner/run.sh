#!/usr/bin/env bash
set -euo pipefail

# Colors for logging
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Paths
readonly CONFIG_PATH=/data/options.json
readonly ESPHOME_CONFIG_BASE="/config/esphome/.esphome"
readonly ADDONS_DATA_PATH="/mnt/data/supervisor/addons/data"
readonly DOCKER_LOGS_PATH="/mnt/data/docker/containers"
readonly SUPERVISOR_LOG="/mnt/data/supervisor/supervisor.log"
readonly HA_LOG_PATH="/config"

# Read configuration
SCHEDULE_ENABLED=$(jq -r '.schedule_enabled // true' "$CONFIG_PATH")
CLEANUP_TIME=$(jq -r '.cleanup_time // "03:30"' "$CONFIG_PATH")
RUN_ON_STARTUP=$(jq -r '.run_on_startup // true' "$CONFIG_PATH")
CLEANUP_ESPHOME=$(jq -r '.cleanup_esphome // true' "$CONFIG_PATH")
CLEANUP_DOCKER_LOGS=$(jq -r '.cleanup_docker_logs // true' "$CONFIG_PATH")
CLEANUP_SUPERVISOR_LOG=$(jq -r '.cleanup_supervisor_log // true' "$CONFIG_PATH")
SUPERVISOR_LOG_LINES=$(jq -r '.supervisor_log_lines // 10000' "$CONFIG_PATH")
CLEANUP_HA_LOGS=$(jq -r '.cleanup_ha_logs // true' "$CONFIG_PATH")
HA_LOG_RETENTION_DAYS=$(jq -r '.ha_log_retention_days // 7' "$CONFIG_PATH")

# Logging functions
log_info() {
    echo -e "${CYAN}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Get disk usage of a path
get_size() {
    local path="$1"
    if [[ -e "$path" ]]; then
        du -sb "$path" 2>/dev/null | awk '{print $1}' || echo "0"
    else
        echo "0"
    fi
}

# Format bytes to human readable
format_bytes() {
    local bytes="$1"
    if (( bytes >= 1073741824 )); then
        printf "%.2f GB" "$(echo "scale=2; $bytes/1073741824" | bc)"
    elif (( bytes >= 1048576 )); then
        printf "%.2f MB" "$(echo "scale=2; $bytes/1048576" | bc)"
    elif (( bytes >= 1024 )); then
        printf "%.2f KB" "$(echo "scale=2; $bytes/1024" | bc)"
    else
        echo "${bytes} bytes"
    fi
}

# Auto-discover ESPHome addon slug
discover_esphome_slug() {
    log_info "Auto-discovering ESPHome add-on slug..."
    
    if [[ ! -d "$ADDONS_DATA_PATH" ]]; then
        log_warn "Add-ons data path not found: $ADDONS_DATA_PATH"
        return 1
    fi
    
    # Find directories matching *_esphome pattern
    local esphome_dirs=()
    while IFS= read -r -d '' dir; do
        esphome_dirs+=("$(basename "$dir")")
    done < <(find "$ADDONS_DATA_PATH" -maxdepth 1 -type d -name "*_esphome" -print0 2>/dev/null)
    
    if [[ ${#esphome_dirs[@]} -eq 0 ]]; then
        log_warn "No ESPHome add-on directory found"
        return 1
    elif [[ ${#esphome_dirs[@]} -gt 1 ]]; then
        log_warn "Multiple ESPHome add-on directories found: ${esphome_dirs[*]}"
        log_info "Using first match: ${esphome_dirs[0]}"
    fi
    
    echo "${esphome_dirs[0]}"
    return 0
}

# Cleanup ESPHome config artifacts
cleanup_esphome_config() {
    if [[ "$CLEANUP_ESPHOME" != "true" ]]; then
        log_info "ESPHome cleanup disabled, skipping..."
        return 0
    fi
    
    log_info "=== Cleaning ESPHome Config Artifacts ==="
    
    local total_freed=0
    local dirs=(
        "build"
        ".pioenvs"
        ".platformio"
        "managed_components"
        "managed_libraries"
    )
    
    for dir in "${dirs[@]}"; do
        local full_path="${ESPHOME_CONFIG_BASE}/${dir}"
        
        if [[ -d "$full_path" ]]; then
            local size_before=$(get_size "$full_path")
            log_info "Deleting: $full_path"
            
            if rm -rf "$full_path" 2>/dev/null; then
                total_freed=$((total_freed + size_before))
                log_success "Deleted: $full_path (freed $(format_bytes "$size_before"))"
            else
                log_error "Failed to delete: $full_path"
            fi
        else
            log_info "Not found (skipping): $full_path"
        fi
    done
    
    log_success "ESPHome config cleanup freed: $(format_bytes "$total_freed")"
}

# Cleanup ESPHome addon data
cleanup_esphome_addon() {
    if [[ "$CLEANUP_ESPHOME" != "true" ]]; then
        return 0
    fi
    
    log_info "=== Cleaning ESPHome Add-on Data ==="
    
    local esphome_slug
    if ! esphome_slug=$(discover_esphome_slug); then
        log_warn "Cannot clean ESPHome add-on data: slug not found"
        return 0
    fi
    
    log_info "Found ESPHome add-on: $esphome_slug"
    
    local total_freed=0
    local addon_base="${ADDONS_DATA_PATH}/${esphome_slug}"
    local dirs=("build" "cache" "packages")
    
    for dir in "${dirs[@]}"; do
        local full_path="${addon_base}/${dir}"
        
        if [[ -d "$full_path" ]]; then
            local size_before=$(get_size "$full_path")
            log_info "Deleting: $full_path"
            
            if rm -rf "$full_path" 2>/dev/null; then
                total_freed=$((total_freed + size_before))
                log_success "Deleted: $full_path (freed $(format_bytes "$size_before"))"
            else
                log_error "Failed to delete: $full_path"
            fi
        else
            log_info "Not found (skipping): $full_path"
        fi
    done
    
    log_success "ESPHome add-on cleanup freed: $(format_bytes "$total_freed")"
}

# Cleanup Docker logs
cleanup_docker_logs() {
    if [[ "$CLEANUP_DOCKER_LOGS" != "true" ]]; then
        log_info "Docker log cleanup disabled, skipping..."
        return 0
    fi
    
    log_info "=== Cleaning Docker Container Logs ==="
    
    if [[ ! -d "$DOCKER_LOGS_PATH" ]]; then
        log_warn "Docker logs path not found: $DOCKER_LOGS_PATH"
        return 0
    fi
    
    local total_freed=0
    local count=0
    
    # Find all *-json.log files
    while IFS= read -r -d '' logfile; do
        if [[ -f "$logfile" ]]; then
            local size_before=$(get_size "$logfile")
            
            if [[ $size_before -gt 0 ]]; then
                log_info "Truncating: $logfile ($(format_bytes "$size_before"))"
                
                if > "$logfile" 2>/dev/null; then
                    total_freed=$((total_freed + size_before))
                    ((count++))
                else
                    log_error "Failed to truncate: $logfile"
                fi
            fi
        fi
    done < <(find "$DOCKER_LOGS_PATH" -type f -name "*-json.log" -print0 2>/dev/null)
    
    log_success "Truncated $count Docker log files, freed: $(format_bytes "$total_freed")"
}

# Cleanup Supervisor log
cleanup_supervisor_log() {
    if [[ "$CLEANUP_SUPERVISOR_LOG" != "true" ]]; then
        log_info "Supervisor log cleanup disabled, skipping..."
        return 0
    fi
    
    log_info "=== Cleaning Supervisor Log ==="
    
    if [[ ! -f "$SUPERVISOR_LOG" ]]; then
        log_warn "Supervisor log not found: $SUPERVISOR_LOG"
        return 0
    fi
    
    local size_before=$(get_size "$SUPERVISOR_LOG")
    log_info "Supervisor log current size: $(format_bytes "$size_before")"
    
    if [[ $SUPERVISOR_LOG_LINES -eq 0 ]]; then
        log_info "Truncating supervisor log to 0 (keep 0 lines)"
        if > "$SUPERVISOR_LOG" 2>/dev/null; then
            log_success "Supervisor log truncated, freed: $(format_bytes "$size_before")"
        else
            log_error "Failed to truncate supervisor log"
        fi
    else
        log_info "Keeping last $SUPERVISOR_LOG_LINES lines of supervisor log"
        local temp_file="${SUPERVISOR_LOG}.tmp"
        
        if tail -n "$SUPERVISOR_LOG_LINES" "$SUPERVISOR_LOG" > "$temp_file" 2>/dev/null; then
            if mv "$temp_file" "$SUPERVISOR_LOG" 2>/dev/null; then
                local size_after=$(get_size "$SUPERVISOR_LOG")
                local freed=$((size_before - size_after))
                log_success "Supervisor log trimmed, freed: $(format_bytes "$freed")"
            else
                log_error "Failed to replace supervisor log"
                rm -f "$temp_file"
            fi
        else
            log_error "Failed to trim supervisor log"
            rm -f "$temp_file"
        fi
    fi
}

# Cleanup Home Assistant rotated logs
cleanup_ha_logs() {
    if [[ "$CLEANUP_HA_LOGS" != "true" ]]; then
        log_info "Home Assistant log cleanup disabled, skipping..."
        return 0
    fi
    
    log_info "=== Cleaning Home Assistant Rotated Logs ==="
    
    if [[ ! -d "$HA_LOG_PATH" ]]; then
        log_warn "HA log path not found: $HA_LOG_PATH"
        return 0
    fi
    
    local total_freed=0
    local count=0
    
    if [[ $HA_LOG_RETENTION_DAYS -eq 0 ]]; then
        log_info "Deleting ALL rotated HA logs (retention set to 0 days)"
        
        while IFS= read -r -d '' logfile; do
            local size_before=$(get_size "$logfile")
            log_info "Deleting: $logfile ($(format_bytes "$size_before"))"
            
            if rm -f "$logfile" 2>/dev/null; then
                total_freed=$((total_freed + size_before))
                ((count++))
            else
                log_error "Failed to delete: $logfile"
            fi
        done < <(find "$HA_LOG_PATH" -maxdepth 1 -type f -name "home-assistant.log.*" -print0 2>/dev/null)
    else
        log_info "Deleting rotated HA logs older than $HA_LOG_RETENTION_DAYS days"
        
        while IFS= read -r -d '' logfile; do
            local size_before=$(get_size "$logfile")
            log_info "Deleting: $logfile ($(format_bytes "$size_before"))"
            
            if rm -f "$logfile" 2>/dev/null; then
                total_freed=$((total_freed + size_before))
                ((count++))
            else
                log_error "Failed to delete: $logfile"
            fi
        done < <(find "$HA_LOG_PATH" -maxdepth 1 -type f -name "home-assistant.log.*" -mtime "+$HA_LOG_RETENTION_DAYS" -print0 2>/dev/null)
    fi
    
    log_success "Deleted $count HA log files, freed: $(format_bytes "$total_freed")"
}

# Main cleanup function
run_cleanup() {
    log_info "╔════════════════════════════════════════════════════════════╗"
    log_info "║        HAOS Maintenance Cleaner - Starting Cleanup        ║"
    log_info "╚════════════════════════════════════════════════════════════╝"
    
    local start_time=$(date +%s)
    
    cleanup_esphome_config
    echo ""
    cleanup_esphome_addon
    echo ""
    cleanup_docker_logs
    echo ""
    cleanup_supervisor_log
    echo ""
    cleanup_ha_logs
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    log_success "╔════════════════════════════════════════════════════════════╗"
    log_success "║           Cleanup Completed in ${duration}s                        ║"
    log_success "╚════════════════════════════════════════════════════════════╝"
}

# Calculate next cleanup time
get_next_cleanup_time() {
    local target_time="$1"
    local now=$(date +%s)
    
    # Parse HH:MM
    local hour minute
    IFS=':' read -r hour minute <<< "$target_time"
    
    # Get today's target time
    local today_target=$(date -d "today ${hour}:${minute}:00" +%s 2>/dev/null || echo "0")
    
    if [[ $today_target -eq 0 ]]; then
        log_error "Invalid cleanup_time format: $target_time (expected HH:MM)"
        return 1
    fi
    
    # If target time has passed today, schedule for tomorrow
    if [[ $now -ge $today_target ]]; then
        date -d "tomorrow ${hour}:${minute}:00" +%s
    else
        echo "$today_target"
    fi
}

# Main scheduler loop
main() {
    log_info "HAOS Maintenance Cleaner starting..."
    log_info "Configuration:"
    log_info "  - Schedule enabled: $SCHEDULE_ENABLED"
    log_info "  - Cleanup time: $CLEANUP_TIME"
    log_info "  - Run on startup: $RUN_ON_STARTUP"
    log_info "  - ESPHome cleanup: $CLEANUP_ESPHOME"
    log_info "  - Docker logs: $CLEANUP_DOCKER_LOGS"
    log_info "  - Supervisor log: $CLEANUP_SUPERVISOR_LOG (keep $SUPERVISOR_LOG_LINES lines)"
    log_info "  - HA logs: $CLEANUP_HA_LOGS (retain $HA_LOG_RETENTION_DAYS days)"
    echo ""
    
    # Run on startup if enabled
    if [[ "$RUN_ON_STARTUP" == "true" ]]; then
        run_cleanup
        echo ""
    fi
    
    # If scheduling is disabled, exit after startup cleanup
    if [[ "$SCHEDULE_ENABLED" != "true" ]]; then
        log_info "Scheduled cleanup disabled. Exiting after startup cleanup."
        exit 0
    fi
    
    # Main scheduling loop
    while true; do
        local next_run
        if ! next_run=$(get_next_cleanup_time "$CLEANUP_TIME"); then
            log_error "Failed to calculate next cleanup time. Sleeping 1 hour..."
            sleep 3600
            continue
        fi
        
        local now=$(date +%s)
        local sleep_seconds=$((next_run - now))
        
        local next_run_human=$(date -d "@$next_run" "+%Y-%m-%d %H:%M:%S")
        log_info "Next cleanup scheduled for: $next_run_human"
        log_info "Sleeping for $sleep_seconds seconds..."
        
        sleep "$sleep_seconds"
        
        run_cleanup
        echo ""
    done
}

# Trap signals for graceful shutdown
trap 'log_info "Received shutdown signal. Exiting..."; exit 0' SIGTERM SIGINT

# Start the main loop
main