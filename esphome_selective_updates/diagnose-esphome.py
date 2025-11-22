#!/usr/bin/env python3
"""
ESPHome Container Diagnostic Script
Run this to diagnose container connectivity issues
"""

import subprocess
import os
import json
from pathlib import Path

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

print("=" * 70)
print("ESPHome Container Diagnostics")
print("=" * 70)
print()

# Check 1: Docker is accessible
print("1. Checking Docker accessibility...")
returncode, stdout, stderr = run_cmd(["docker", "version"])
if returncode == 0:
    print("   ✓ Docker is accessible")
else:
    print(f"   ✗ Docker not accessible: {stderr}")
    exit(1)

print()

# Check 2: List all running containers
print("2. Listing all running containers...")
returncode, stdout, stderr = run_cmd(["docker", "ps", "--format", "{{.Names}}"])
if returncode == 0:
    containers = stdout.strip().split('\n')
    print(f"   Found {len(containers)} running containers:")
    for container in containers:
        if container:
            print(f"     - {container}")
else:
    print(f"   ✗ Failed to list containers: {stderr}")
    exit(1)

print()

# Check 3: Find ESPHome container
print("3. Looking for ESPHome container...")
esphome_containers = [c for c in containers if 'esphome' in c.lower()]
if esphome_containers:
    print(f"   ✓ Found ESPHome container(s):")
    for container in esphome_containers:
        print(f"     - {container}")
    
    esphome_container = esphome_containers[0]
else:
    print("   ✗ No ESPHome container found")
    print("   Please start the ESPHome add-on first")
    exit(1)

print()

# Check 4: Test docker exec into container
print(f"4. Testing docker exec into '{esphome_container}'...")
returncode, stdout, stderr = run_cmd(["docker", "exec", esphome_container, "ls", "/config"])
if returncode == 0:
    print(f"   ✓ Can execute commands in container")
    print(f"   Container /config contents: {stdout.strip()}")
else:
    print(f"   ✗ Cannot exec into container: {stderr}")
    exit(1)

print()

# Check 5: Check if esphome binary exists in container
print("5. Checking if esphome binary exists in container...")
returncode, stdout, stderr = run_cmd(["docker", "exec", esphome_container, "which", "esphome"])
if returncode == 0:
    print(f"   ✓ ESPHome binary found at: {stdout.strip()}")
else:
    print(f"   ✗ ESPHome binary not found in container")
    exit(1)

print()

# Check 6: Test esphome version command
print("6. Testing esphome version command...")
returncode, stdout, stderr = run_cmd(["docker", "exec", esphome_container, "esphome", "version"])
if returncode == 0:
    print(f"   ✓ ESPHome version command works")
    print(f"   Output: {stdout.strip()}")
else:
    print(f"   ✗ ESPHome version command failed")
    print(f"   Stderr: {stderr}")
    exit(1)

print()

# Check 7: Check if /config/esphome directory exists
print("7. Checking /config/esphome directory...")
returncode, stdout, stderr = run_cmd(["docker", "exec", esphome_container, "ls", "/config/esphome"])
if returncode == 0:
    yaml_files = [f for f in stdout.strip().split('\n') if f.endswith('.yaml')]
    print(f"   ✓ /config/esphome directory exists")
    print(f"   Found {len(yaml_files)} YAML files")
    if yaml_files:
        print(f"   First few YAML files:")
        for f in yaml_files[:5]:
            print(f"     - {f}")
else:
    print(f"   ✗ /config/esphome directory not accessible: {stderr}")
    exit(1)

print()

# Check 8: Try to run esphome version on a real YAML file
if yaml_files:
    test_yaml = yaml_files[0]
    print(f"8. Testing esphome version on '{test_yaml}'...")
    returncode, stdout, stderr = run_cmd([
        "docker", "exec", esphome_container, 
        "esphome", "version", f"/config/esphome/{test_yaml}"
    ])
    if returncode == 0:
        print(f"   ✓ ESPHome version command works on YAML files")
        print(f"   Output: {stdout.strip()[:200]}")
    else:
        print(f"   ✗ ESPome version command failed")
        print(f"   Stdout: {stdout[:200]}")
        print(f"   Stderr: {stderr[:200]}")

print()

# Check 9: Check environment variable
print("9. Checking ESPHOME_CONTAINER environment variable...")
env_container = os.environ.get("ESPHOME_CONTAINER", "")
if env_container:
    print(f"   ✓ ESPHOME_CONTAINER is set to: {env_container}")
    if env_container == esphome_container:
        print(f"   ✓ Matches detected container")
    else:
        print(f"   ⚠ Does NOT match detected container '{esphome_container}'")
        print(f"   You may need to update run.sh")
else:
    print(f"   ✗ ESPHOME_CONTAINER not set")
    print(f"   Should be set to: {esphome_container}")

print()
print("=" * 70)
print("Diagnostic Summary")
print("=" * 70)
print(f"Docker: ✓")
print(f"ESPHome Container: {esphome_container}")
print(f"ESPHome Binary: ✓")
print(f"Config Directory: ✓")
print(f"YAML Files: {len(yaml_files)}")
print()
print(f"Recommended ESPHOME_CONTAINER value for run.sh:")
print(f"  export ESPHOME_CONTAINER=\"{esphome_container}\"")
print("=" * 70)