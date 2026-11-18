"""Validated data loading and deterministic historical basket calculations."""
from pathlib import Path
import json
from urllib.parse import urlencode
import pandas as pd
import numpy as np

SNAPSHOT_DIR = Path(__file__).resolve().parent / 'snapshot'
DATA_DIR = SNAPSHOT_DIR
SNAPSHOT_FILES = tuple(f'part-{index:02}.parquet' for index in range(1, 5)) + (
    'lookup_item.csv', 'lookup_premise.csv', 'audit.json',
)


def deployment_sources():
    return tuple(SNAPSHOT_DIR / name for name in SNAPSHOT_FILES)


def load_data():
    import pyarrow.parquet as parquet

    sources = deployment_sources()
    missing = [path.name for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError('Missing files from snapshot/: ' + ', '.join(missing))
    parts = [str(path) for path in sources if path.suffix == '.parquet']
    data = parquet.read_table(parts).to_pandas()
    items = pd.read_csv(SNAPSHOT_DIR / 'lookup_item.csv')
    shops = pd.read_csv(SNAPSHOT_DIR / 'lookup_premise.csv')
    audit = json.loads((SNAPSHOT_DIR / 'audit.json').read_text(encoding='utf-8'))
    if len(data) != audit['Eligible observations']:
        raise ValueError('Snapshot row count differs from the data audit.')
    return data, items, shops, audit


def latest_prices(data, reference, days=7):
    reference = pd.Timestamp(reference)
    start = reference - pd.Timedelta(days=days - 1)
    result = data.loc[data.date.between(start, reference)].sort_values('date').drop_duplicates(['premise_code', 'item_code'], keep='last').copy()
    result['age_days'] = (reference - result.date).dt.days
    return result

def basket_results(latest, quantities, premise_codes):
    if not quantities or any(not np.isfinite(q) or q <= 0 for q in quantities.values()):
        raise ValueError('Choose at least one item and positive finite quantities.')
    rows = latest[latest.item_code.isin(quantities)].copy()
    rows['quantity'] = rows.item_code.map(quantities).astype(float)
    rows['line_total'] = rows.price * rows.quantity
    present = rows.groupby('premise_code').item_code.agg(set)
    missing = pd.DataFrame({'premise_code': list(premise_codes)})
    missing['missing_codes'] = missing.premise_code.map(lambda p: sorted(set(quantities) - present.get(p, set())))
    complete_codes = missing.loc[missing.missing_codes.map(len).eq(0), 'premise_code']
    complete = rows[rows.premise_code.isin(complete_codes)].groupby('premise_code', as_index=False).agg(total=('line_total', 'sum'), oldest=('date', 'min'), newest=('date', 'max'))
    complete = complete.sort_values(['total', 'premise_code'])
    multi = rows.sort_values(['price', 'premise_code']).drop_duplicates('item_code')
    absent = sorted(set(quantities) - set(multi.item_code))
    return rows, complete, missing[missing.missing_codes.map(len).gt(0)], multi, absent

def maps_url(row):
    return 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': f"{row['premise']}, {row['address']}, {row['district']}, {row['state']}, Malaysia"})
