#!/usr/bin/env python3
"""
Network Monitoring Suite - Main Runner

This script provides a unified interface to run all network monitoring tools
individually or as a complete monitoring suite.

Usage Examples:
    # Run all monitoring scripts
    python run_monitoring.py --all

    # Run specific scripts
    python run_monitoring.py --health --discovery

    # Run with filters
    python run_monitoring.py --health --site datacenter1

    # Run with custom config
    python run_monitoring.py --all --config custom_config.yaml

Author: Network Monitoring Suite
Version: 1.0
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add scripts directory to path
scripts_dir = Path(__file__).parent / 'scripts'
sys.path.append(str(scripts_dir))

# Import all monitoring modules
try:
    from device_discovery import main as discovery_main
    from health_check import main as health_main
    from port_mapper import main as port_main
    from vlan_audit import main as vlan_main
    from interface_monitor import main as interface_main
    from change_logger import main as change_main
    from stp_analyzer import main as stp_main
except ImportError as e:
    print(f"Error importing monitoring modules: {e}")
    sys.exit(1)


class MonitoringSuite:
    """Main monitoring suite coordinator"""
    
    def __init__(self, config_file: str = 'config/config.yaml'):
        """Initialize the monitoring suite"""
        self.config_file = config_file
        self.results = {}
        self.start_time = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/monitoring_suite_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MonitoringSuite')
    
    def run_script(self, script_name: str, script_main, args: List[str]) -> Dict:
        """Run a monitoring script with error handling"""
        self.logger.info(f"Starting {script_name}...")
        
        start_time = time.time()
        result = {
            'name': script_name,
            'status': 'unknown',
            'duration': 0.0,
            'exit_code': 0,
            'error': None,
            'output_files': []
        }
        
        try:
            # Temporarily modify sys.argv for the script
            original_argv = sys.argv.copy()
            sys.argv = ['script'] + args
            
            # Run the script
            script_main()
            
            result['status'] = 'success'
            result['exit_code'] = 0
            
        except SystemExit as e:
            result['exit_code'] = e.code or 0
            if e.code in [0, None]:
                result['status'] = 'success'
            elif e.code == 1:
                result['status'] = 'warning'
            else:
                result['status'] = 'error'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['exit_code'] = 1
            self.logger.error(f"Error in {script_name}: {e}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
            result['duration'] = time.time() - start_time
        
        self.logger.info(f"Completed {script_name} in {result['duration']:.2f}s - Status: {result['status']}")
        return result
    
    def run_monitoring_suite(self, scripts: List[str], common_args: List[str]) -> Dict:
        """Run the complete monitoring suite"""
        self.start_time = time.time()
        
        print("🚀 Starting Network Monitoring Suite")
        print("=" * 50)
        
        # Script mapping
        script_mapping = {
            'discovery': (discovery_main, "Device Discovery & Inventory"),
            'health': (health_main, "Universal Health Check Dashboard"),
            'port': (port_main, "Port Mapping & Documentation"),
            'vlan': (vlan_main, "VLAN Auditor"),
            'interface': (interface_main, "Interface Error Monitor"),
            'change': (change_main, "Network Change Logger"),
            'stp': (stp_main, "Spanning Tree Analyzer")
        }
        
        results = {}
        
        for script in scripts:
            if script in script_mapping:
                script_main, description = script_mapping[script]
                print(f"\n📊 Running {description}...")
                
                # Prepare arguments for this script
                script_args = common_args.copy()
                script_args.extend(['--config', self.config_file])
                
                # Run the script
                result = self.run_script(script, script_main, script_args)
                results[script] = result
            else:
                print(f"❌ Unknown script: {script}")
        
        # Generate summary report
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results: Dict):
        """Generate a summary report of all monitoring results"""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 50)
        print("📋 MONITORING SUITE SUMMARY REPORT")
        print("=" * 50)
        
        print(f"🕐 Total execution time: {total_duration:.2f} seconds")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Scripts executed: {len(results)}")
        
        # Status summary
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        warning_count = sum(1 for r in results.values() if r['status'] == 'warning')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        print(f"\n📈 Execution Summary:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ⚠️  Warnings: {warning_count}")
        print(f"  ❌ Errors: {error_count}")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for script, result in results.items():
            status_icon = {
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            print(f"  {status_icon} {script.capitalize()}: {result['status']} ({result['duration']:.2f}s)")
            if result['error']:
                print(f"      Error: {result['error']}")
        
        # Overall status
        if error_count > 0:
            print(f"\n🚨 OVERALL STATUS: FAILED ({error_count} errors)")
            exit_code = 2
        elif warning_count > 0:
            print(f"\n⚠️  OVERALL STATUS: COMPLETED WITH WARNINGS ({warning_count} warnings)")
            exit_code = 1
        else:
            print(f"\n🎉 OVERALL STATUS: SUCCESS")
            exit_code = 0
        
        print("\n" + "=" * 50)
        
        # Save summary report
        self.save_summary_report(results, total_duration)
        
        return exit_code
    
    def save_summary_report(self, results: Dict, total_duration: float):
        """Save summary report to file"""
        try:
            summary_data = {
                'execution_summary': {
                    'timestamp': datetime.now().isoformat(),
                    'total_duration': total_duration,
                    'scripts_executed': len(results),
                    'success_count': sum(1 for r in results.values() if r['status'] == 'success'),
                    'warning_count': sum(1 for r in results.values() if r['status'] == 'warning'),
                    'error_count': sum(1 for r in results.values() if r['status'] == 'error')
                },
                'script_results': results
            }
            
            # Save as JSON
            import json
            os.makedirs('output', exist_ok=True)
            summary_file = f"output/monitoring_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            
            print(f"📄 Summary report saved to: {summary_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save summary report: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Network Monitoring Suite - Unified Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                           # Run all monitoring scripts
  %(prog)s --health --discovery            # Run health check and discovery
  %(prog)s --all --site datacenter1        # Run all with site filter
  %(prog)s --interface --verbose           # Run interface monitor with verbose output
  %(prog)s --change --continuous           # Run change logger continuously

Individual Scripts:
  --discovery    Device Discovery & Inventory
  --health       Universal Health Check Dashboard  
  --port         Port Mapping & Documentation
  --vlan         VLAN Auditor
  --interface    Interface Error Monitor
  --change       Network Change Logger
  --stp          Spanning Tree Analyzer
        """
    )
    
    # Script selection
    parser.add_argument('--all', action='store_true',
                       help='Run all monitoring scripts')
    parser.add_argument('--discovery', action='store_true',
                       help='Run device discovery script')
    parser.add_argument('--health', action='store_true',
                       help='Run health check script')
    parser.add_argument('--port', action='store_true',
                       help='Run port mapping script')
    parser.add_argument('--vlan', action='store_true',
                       help='Run VLAN audit script')
    parser.add_argument('--interface', action='store_true',
                       help='Run interface monitor script')
    parser.add_argument('--change', action='store_true',
                       help='Run change logger script')
    parser.add_argument('--stp', action='store_true',
                       help='Run STP analyzer script')
    
    # Common arguments
    parser.add_argument('--config', default='config/config.yaml',
                       help='Configuration file path')
    parser.add_argument('--output-formats', nargs='+',
                       choices=['json', 'csv', 'html', 'excel', 'pdf'],
                       default=['json', 'html'],
                       help='Output formats for reports')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Maximum concurrent workers')
    parser.add_argument('--timeout', type=int, default=60,
                       help='Operation timeout in seconds')
    
    # Filters
    parser.add_argument('--site', help='Filter by site')
    parser.add_argument('--vendor', help='Filter by vendor')
    parser.add_argument('--role', help='Filter by device role')
    
    # Options
    parser.add_argument('--send-alerts', action='store_true',
                       help='Send notifications for critical issues')
    parser.add_argument('--continuous', action='store_true',
                       help='Run in continuous monitoring mode (for change logger)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Monitoring interval for continuous mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Determine which scripts to run
    scripts_to_run = []
    
    if args.all:
        scripts_to_run = ['discovery', 'health', 'port', 'vlan', 'interface', 'change', 'stp']
    else:
        if args.discovery:
            scripts_to_run.append('discovery')
        if args.health:
            scripts_to_run.append('health')
        if args.port:
            scripts_to_run.append('port')
        if args.vlan:
            scripts_to_run.append('vlan')
        if args.interface:
            scripts_to_run.append('interface')
        if args.change:
            scripts_to_run.append('change')
        if args.stp:
            scripts_to_run.append('stp')
    
    if not scripts_to_run:
        parser.print_help()
        print("\n❌ No monitoring scripts selected. Use --all or specify individual scripts.")
        sys.exit(1)
    
    # Prepare common arguments
    common_args = []
    
    if args.output_formats:
        common_args.extend(['--output-formats'] + args.output_formats)
    if args.max_workers:
        common_args.extend(['--max-workers', str(args.max_workers)])
    if args.timeout:
        common_args.extend(['--timeout', str(args.timeout)])
    if args.site:
        common_args.extend(['--site', args.site])
    if args.vendor:
        common_args.extend(['--vendor', args.vendor])
    if args.role:
        common_args.extend(['--role', args.role])
    if args.send_alerts:
        common_args.append('--send-alerts')
    if args.continuous and 'change' in scripts_to_run:
        common_args.append('--continuous')
        common_args.extend(['--interval', str(args.interval)])
    if args.verbose:
        common_args.append('--verbose')
    
    try:
        # Initialize monitoring suite
        suite = MonitoringSuite(args.config)
        
        # Run the monitoring suite
        results = suite.run_monitoring_suite(scripts_to_run, common_args)
        
        # Generate final exit code
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        warning_count = sum(1 for r in results.values() if r['status'] == 'warning')
        
        if error_count > 0:
            sys.exit(2)
        elif warning_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running monitoring suite: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()