import json
from pathlib import Path
import sys

import plan_io
from carol_eval_a import buzz, decode48

root = Path(sys.argv[1]).resolve()
revision = sys.argv[2]
limit = plan_io.RENDER['source_buzz_max_db']
rows = {}
for style in plan_io.styles_for(root, revision):
    source = root / style / revision / 'src_A.wav'
    median, maximum = buzz(decode48(str(source)))
    rows[style] = {'source_sha256': plan_io.digest(source), 'buzz_median_db': round(median, 2), 'buzz_max_db': round(maximum, 2), 'limit_buzz_max_db': limit, 'pass': maximum <= limit}
report = {'method': 'carol_eval_a.buzz on src_A.wav: 5 s Hann windows, 2-6 kHz energy share of mono mix, loud inner windows; PM gate buzz_max <= limit', 'styles': rows, 'all_pass': all(row['pass'] for row in rows.values())}
plan_io.save(root / f'{revision}-run' / 'source-buzz.json', report)
print(json.dumps({style: [row['buzz_median_db'], row['buzz_max_db'], row['pass']] for style, row in rows.items()}), flush=True)
sys.exit(0 if report['all_pass'] else 4)
