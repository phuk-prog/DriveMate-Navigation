"""Execute available research checks; never infer consumer-app results."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

CHECKS = {
    'positioning': ['benchmarks.gps_validation'],
    'gps_recovery': ['benchmarks.gps_recovery_validation'],
    'instruction_timing': ['benchmarks.instruction_validation'],
    'whole_drive': ['benchmarks.whole_drive'],
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category', choices=['all', *CHECKS], default='all')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'results' / 'category-execution'
    output.mkdir(parents=True, exist_ok=True)
    names = list(CHECKS) if args.category == 'all' else [args.category]
    rows = []
    for name in names:
        for module in CHECKS[name]:
            started = time.monotonic()
            try:
                result = subprocess.run([sys.executable, '-m', module], cwd=root,
                    capture_output=True, text=True, timeout=180)
                code, log = result.returncode, result.stdout + result.stderr
                status = 'passed' if code == 0 else 'failed'
            except subprocess.TimeoutExpired as error:
                code, status, log = None, 'timeout', str(error)
            (output / (name + '.log')).write_text(log)
            row = {'category': name, 'status': status, 'returncode': code,
                'wall_seconds': round(time.monotonic() - started, 3),
                'evidence': str(output / (name + '.log'))}
            rows.append(row)
            print(json.dumps(row), flush=True)
    report = {'system': 'DriveMate research prototype',
        'test_class': 'synthetic; no consumer-app or real-road comparison',
        'scores': None, 'checks': rows}
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    return 1 if any(row['status'] != 'passed' for row in rows) else 0

if __name__ == '__main__':
    raise SystemExit(main())
