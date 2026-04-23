import json
import os

def check():
    results = {}
    
    # Phase 0
    with open('/tmp/phase0_finalcheck.json') as f:
        p0 = json.load(f)
    results['phase0'] = 'PASS' if (
        p0['runtime']['phase'] == 'phase0' and 
        not p0.get('generated_artifacts') and 
        len(p0.get('errors', [])) == 0
    ) else 'FAIL'

    # Phase 1
    with open('/tmp/phase1_finalcheck.json') as f:
        p1 = json.load(f)
    p1_artifacts = p1.get('generated_artifacts', {})
    results['phase1'] = 'PASS' if (
        p1['runtime']['phase'] == 'phase1' and 
        all(k in p1_artifacts for k in ['readme', 'architecture', 'improvements']) and 
        len(p1.get('errors', [])) == 0
    ) else 'FAIL'

    # Phase 2
    with open('/tmp/phase2_finalcheck.json') as f:
        p2 = json.load(f)
    p2_artifacts = p2.get('generated_artifacts', {})
    results['phase2'] = 'PASS' if (
        p2['runtime']['phase'] == 'phase2' and 
        all(k in p2_artifacts for k in ['readme', 'architecture', 'improvements', 'perception']) and 
        len(p2.get('errors', [])) == 0
    ) else 'FAIL'

    # Phase 2 diagnostics
    diag = p2.get('diagnostics', {})
    results['phase2 diagnostics'] = 'PASS' if (
        diag.get('app_status') in ['started_by_agent', 'already_running'] and 
        diag.get('local_url_configured') is True
    ) else 'FAIL'

    # Phase 2 summary
    summary = p2.get('summary', {})
    results['phase2 summary'] = 'PASS' if (
        summary.get('screens_reachable', 0) >= 2 and 
        summary.get('screens_with_screenshot', 0) >= 2 and 
        summary.get('flows_detected', 0) >= 1
    ) else 'FAIL'

    # Phase 2 deliverables (at least one screen has related_files non-empty)
    deliverables = p2.get('deliverables', {})
    screens = deliverables.get('screens', [])
    results['phase2 deliverables'] = 'PASS' if any(s.get('related_files') for s in screens) else 'FAIL'

    # perception.md exists
    results['docs/perception.md exists'] = 'PASS' if os.path.exists('docs/perception.md') else 'FAIL'

    for k, v in results.items():
        print(f"{k}: {v}")

    print("\nMetrics:")
    print(f"screens_reachable: {summary.get('screens_reachable')}")
    print(f"screens_with_screenshot: {summary.get('screens_with_screenshot')}")
    print(f"flows_detected: {summary.get('flows_detected')}")
    print(f"app_status: {diag.get('app_status')}")
    print(f"local_url_configured: {diag.get('local_url_configured')}")

check()
