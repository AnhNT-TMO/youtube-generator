import json
from pathlib import Path
import sys

import plan_io

work = Path(sys.argv[1])
path = work / 'picks.json'
picks = plan_io.load(path)
keys = plan_io.load(work / 'key_gate.json')
order = plan_io.PIPELINE['selection_order']
technical = set(picks['retained_takes']) | set(picks.get('other_passing_takes', []))
takes = {name: item for name, item in keys['files'].items() if item['role'] == 'take'}
key_pass = {name for name, item in takes.items() if item['pass']}
passing = [name for name in order if name in technical and name in key_pass and keys['method_valid_on_source']]
original = picks.get('pm_choice_policy', {}).get('original_score_pick', picks['picks_instr'])
picks.pop('provisional_picks', None)
picks['picks_instr'] = passing[:1]
picks['backups'] = passing[1:2]
picks['key_gate'] = {'rule': 'official restricted planned-key gate', 'min_margin': keys['min_margin'], 'method_valid_on_source': keys['method_valid_on_source'], 'technical_pass': sorted(technical), 'key_pass': sorted(key_pass), 'all_gates_pass': passing,
                     'per_take': {name: [(row['section_id'], row['estimated'], row['margin_vs_next_candidate'], row['pass']) for row in item['sections']] for name, item in keys['files'].items()}}
picks['pm_choice_policy'] = {'selection_order': order, 'original_score_pick': original, 'regeneration': False}
if passing:
    picks['status'] = 'ready_for_listening'
elif not keys['method_valid_on_source']:
    picks['status'] = 'BLOCKED_key_gate_invalid_on_source'
else:
    picks['status'] = 'BLOCKED_no_take_passes_all_gates'
path.write_text(json.dumps(picks, indent=2) + '\n')
print(json.dumps({'style': work.parent.name, 'status': picks['status'], 'picks_instr': picks['picks_instr'], 'backups': picks['backups'], 'technical': sorted(technical), 'key_pass': sorted(key_pass)}), flush=True)
sys.exit(0 if passing else 3)
