"""Strict CSV source import; importing never changes a reconciled snapshot."""
import csv
import hashlib
import io
import json
from .schemas import TransactionCreate


def parse_csv(text: str, currency: str = 'EUR') -> list[dict]:
    if len(text.encode('utf-8')) > 2_000_000:
        raise ValueError('CSV exceeds 2 MB')
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required = {'date', 'description', 'amount_minor'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError('Required columns: date,description,amount_minor')
    rows = []
    for index, row in enumerate(reader, 2):
        if index > 1001:
            raise ValueError('Maximum 1000 rows per import')
        raw = (row.get('amount_minor') or '').strip()
        if not raw or not raw.lstrip('-').isdigit():
            raise ValueError(f'Row {index}: amount_minor must be integer cents')
        item = TransactionCreate(date=row.get('date', ''),
            description=row.get('description', ''), amount_minor=int(raw),
            currency=row.get('currency') or currency,
            category=row.get('category') or 'uncategorized',
            external_id=row.get('external_id') or None).model_dump(mode='json')
        # Identical rows with no source ID are treated as the same source event.
        # Real repeated purchases require distinct external_id values.
        basis = {'source_id': item['external_id']} if item['external_id'] else item
        item['source_key'] = hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()
        rows.append(item)
    return rows
