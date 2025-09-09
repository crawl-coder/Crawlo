#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyze duplicate URLs from instance log files
"""
import os
import glob
from collections import defaultdict

def analyze_duplicates():
    """Analyze duplicate URLs across instance log files"""
    # Find all instance log files
    log_files = glob.glob("instance_*_urls.log")
    
    if not log_files:
        print("No instance log files found!")
        return
    
    print(f"Found {len(log_files)} instance log files:")
    for log_file in log_files:
        print(f"  - {log_file}")
    
    # Collect all URLs and their instances
    url_instances = defaultdict(list)
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                # Skip comment lines
                if line.startswith('#'):
                    continue
                    
                # Parse URL line (URL, Status, InstanceID)
                parts = line.strip().split(', ')
                if len(parts) >= 3:
                    url = parts[0]
                    instance_id = parts[2]
                    url_instances[url].append(instance_id)
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
    
    # Find duplicates
    duplicates = {url: instances for url, instances in url_instances.items() if len(instances) > 1}
    
    print(f"\nAnalyzed {len(url_instances)} unique URLs")
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate URLs:")
        for url, instances in duplicates.items():
            print(f"  {url}")
            print(f"    Processed by instances: {', '.join(instances)}")
    else:
        print("\nNo duplicate URLs found! All instances processed unique URLs.")

if __name__ == '__main__':
    analyze_duplicates()