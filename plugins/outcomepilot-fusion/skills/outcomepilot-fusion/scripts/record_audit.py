#!/usr/bin/env python3
"""Advisory record-coherence checker. Never attests evidence truth or host authorization.

Portable Python 3.9+ / standard library only. Zero side effects on target systems.
Input records are untrusted; invalid shape is reported as INVALID_STATE, not an exception.
"""
import argparse
import json
import sys
from pathlib import Path

CRITERION_STATES = frozenset(('PASS', 'FAIL', 'UNVERIFIED', 'NOT_RUN'))
EVIDENCE_KINDS = frozenset(('SOURCE_CHECK', 'FILE_CHECK', 'DIRECT_TEST', 'OBSERVED_EFFECT', 'READ_BACK', 'OTHER'))
ACTION_KINDS = frozenset(('READ', 'ANALYZE', 'LOCAL_EDIT', 'EXTERNAL_WRITE', 'COMMITMENT'))
ACTION_STATES = frozenset(('PLANNED', 'DONE', 'FAILED', 'UNKNOWN', 'SKIPPED'))
APPROVAL = frozenset(('NOT_REQUIRED', 'REQUIRED_PENDING', 'CLAIMED_APPROVED', 'HOST_CONFIRMED'))
TOP_KEYS = frozenset(('objective', 'max_steps', 'used_steps', 'cancelled', 'unsafe', 'useful_partial',
                      'next_action_id', 'criteria', 'evidence', 'actions'))
CRITERION_KEYS = frozenset(('id', 'description', 'required', 'status', 'evidence_ids'))
EVIDENCE_KEYS = frozenset(('id', 'kind', 'check_result', 'source', 'criterion_ids', 'notes'))
ACTION_KEYS = frozenset(('id', 'kind', 'status', 'target', 'authorization', 'receipt_evidence_ids',
                         'postcondition_evidence_ids', 'ambiguous', 'reconciled'))
POST_KINDS = frozenset(('READ_BACK', 'OBSERVED_EFFECT', 'DIRECT_TEST'))


def _error_unknown(item, allowed, ident, errors):
    for key in item.keys() - allowed:
        errors.append(f'{ident}: unknown field {key}')


def _items(value, section, allowed, errors):
    found = {}
    if not isinstance(value, list):
        errors.append(f'{section} must be an array')
        return found
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f'{section}[{idx}] must be an object')
            continue
        _error_unknown(item, allowed, f'{section}[{idx}]', errors)
        key = item.get('id')
        if not isinstance(key, str) or not key.strip():
            errors.append(f'{section}[{idx}].id must be nonempty string')
            continue
        if key in found:
            errors.append(f'{section} contains duplicate id {key}')
        found[key] = item
    return found


def _links(item, name, ident, errors):
    value = item.get(name)
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        errors.append(f'{ident}.{name} must be an array of nonempty strings')
        return []
    if len(value) != len(set(value)):
        errors.append(f'{ident}.{name} contains duplicate link')
    return value


def audit(record):
    errors = []
    if not isinstance(record, dict):
        return {'status': 'INVALID_STATE', 'errors': ['Record must be an object']}
    _error_unknown(record, TOP_KEYS, 'record', errors)
    if not isinstance(record.get('objective'), str) or not record['objective'].strip():
        errors.append('objective must be nonempty string')
    for key, minimum in (('max_steps', 1), ('used_steps', 0)):
        value = record.get(key)
        if type(value) is not int or value < minimum:
            errors.append(f'{key} must be integer >= {minimum}')
    if type(record.get('max_steps')) is int and type(record.get('used_steps')) is int:
        if record['max_steps'] > 0 and record['used_steps'] > record['max_steps']:
            errors.append('used_steps exceeds max_steps')
    for key in ('cancelled', 'unsafe', 'useful_partial'):
        if key in record and type(record[key]) is not bool:
            errors.append(f'{key} must be boolean')

    criteria = _items(record.get('criteria'), 'criteria', CRITERION_KEYS, errors)
    evidence = _items(record.get('evidence'), 'evidence', EVIDENCE_KEYS, errors)
    actions = _items(record.get('actions'), 'actions', ACTION_KEYS, errors)
    if not criteria:
        errors.append('At least one acceptance criterion is required')
    if criteria and not any(c.get('required') is True for c in criteria.values()):
        errors.append('At least one mandatory acceptance criterion is required')

    c_links = {}
    e_links = {}
    for cid, c in criteria.items():
        if type(c.get('required')) is not bool or c.get('status') not in CRITERION_STATES:
            errors.append(f'Invalid required/status for criterion {cid}')
        if 'description' in c and not isinstance(c['description'], str):
            errors.append(f'Invalid description for criterion {cid}')
        c_links[cid] = _links(c, 'evidence_ids', cid, errors)

    for eid, e in evidence.items():
        if e.get('kind') not in EVIDENCE_KINDS or e.get('check_result') not in CRITERION_STATES:
            errors.append(f'Invalid kind/check_result for evidence {eid}')
        if not isinstance(e.get('source'), str) or not e['source'].strip():
            errors.append(f'Evidence {eid} has no source')
        if 'notes' in e and not isinstance(e['notes'], str):
            errors.append(f'Invalid notes for evidence {eid}')
        e_links[eid] = _links(e, 'criterion_ids', eid, errors)

    for cid, c in criteria.items():
        links = c_links[cid]
        for eid in links:
            if eid not in evidence:
                errors.append(f'Criterion {cid} references missing evidence {eid}')
            elif cid not in e_links[eid]:
                errors.append(f'Nonreciprocal criterion/evidence link: {cid}/{eid}')
        if c.get('status') == 'PASS':
            valid = [eid for eid in links if eid in evidence and evidence[eid].get('check_result') == 'PASS'
                     and cid in e_links[eid]]
            if not valid:
                errors.append(f'PASS criterion {cid} has no passing reciprocal evidence')
            if any(eid in evidence and evidence[eid].get('check_result') == 'FAIL' for eid in links):
                errors.append(f'PASS criterion {cid} has unresolved failing linked evidence')

    for eid, e in evidence.items():
        for cid in e_links[eid]:
            if cid not in criteria:
                errors.append(f'Evidence {eid} references missing criterion {cid}')
            elif eid not in c_links[cid]:
                errors.append(f'Nonreciprocal evidence/criterion link: {eid}/{cid}')

    for aid, a in actions.items():
        if a.get('kind') not in ACTION_KINDS or a.get('status') not in ACTION_STATES:
            errors.append(f'Invalid kind/status for action {aid}')
        if a.get('authorization') not in APPROVAL:
            errors.append(f'Invalid authorization for action {aid}')
        if not isinstance(a.get('target'), str) or not a['target'].strip():
            errors.append(f'Action {aid} missing target')
        if type(a.get('ambiguous')) is not bool or type(a.get('reconciled')) is not bool:
            errors.append(f'Action {aid} needs boolean ambiguous/reconciled')
        receipts = _links(a, 'receipt_evidence_ids', aid, errors)
        post = _links(a, 'postcondition_evidence_ids', aid, errors)
        for eid in receipts + post:
            if eid not in evidence:
                errors.append(f'Action {aid} references missing evidence {eid}')
        if a.get('status') == 'DONE' and a.get('authorization') == 'REQUIRED_PENDING':
            errors.append(f'DONE action {aid} cannot retain pending authorization')
        if a.get('kind') in ('EXTERNAL_WRITE', 'COMMITMENT') and a.get('status') == 'DONE':
            if a.get('authorization') != 'HOST_CONFIRMED':
                errors.append(f'External DONE action {aid} lacks recorded HOST_CONFIRMED approval (not actual proof)')
            if not receipts or not any(eid in evidence and evidence[eid].get('check_result') == 'PASS'
                                       for eid in receipts):
                errors.append(f'External DONE action {aid} lacks passing recorded receipt')
            if not post or not any(eid in evidence and evidence[eid].get('kind') in POST_KINDS
                                   and evidence[eid].get('check_result') == 'PASS' for eid in post):
                errors.append(f'External DONE action {aid} lacks recorded observed postcondition')
            if set(receipts).intersection(post):
                errors.append(f'External DONE action {aid} reuses receipt as postcondition evidence')
        if a.get('status') == 'DONE' and a.get('ambiguous') is True and a.get('reconciled') is False:
            errors.append(f'DONE action {aid} has unresolved ambiguity')

    next_id = record.get('next_action_id')
    if next_id is not None and (not isinstance(next_id, str) or next_id not in actions):
        errors.append('next_action_id must be registered action ID or null')
    if isinstance(next_id, str) and next_id in actions and actions[next_id].get('status') != 'PLANNED':
        errors.append('next_action_id must refer to PLANNED action')
    if errors:
        return {'status': 'INVALID_STATE', 'errors': sorted(set(errors))}

    # Advisory ledger statuses only: even a perfect record can be fabricated.
    if record.get('cancelled'):
        status = 'CANCELLED'
    elif record.get('unsafe'):
        status = 'UNSAFE'
    elif any(a['status'] == 'UNKNOWN' or (a['ambiguous'] and not a['reconciled'])
             for a in actions.values() if a['kind'] in ('EXTERNAL_WRITE', 'COMMITMENT')):
        status = 'BLOCKED'
    elif (all(c['status'] == 'PASS' for c in criteria.values() if c['required'])
          and not any(a['status'] in ('PLANNED', 'UNKNOWN', 'FAILED') for a in actions.values())):
        status = 'RECORDED_COMPLETE'
    elif record['used_steps'] >= record['max_steps']:
        status = 'BUDGET_EXHAUSTED'
    elif any(a['kind'] in ('EXTERNAL_WRITE', 'COMMITMENT') and a['status'] == 'PLANNED'
             and a['authorization'] != 'HOST_CONFIRMED' for a in actions.values()):
        status = 'APPROVAL_REQUIRED'
    elif record.get('useful_partial') and any(c['required'] and c['status'] == 'PASS' for c in criteria.values()):
        status = 'RECORDED_PARTIAL'
    elif next_id:
        status = 'WORK_REMAINING'
    else:
        status = 'BLOCKED'
    return {'status': status, 'errors': [],
            'warning': 'Record coherence ONLY: no fact checking, authorization, actual external effect or independent SUCCESS.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path, help='JSON record path')
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        print(json.dumps({'status': 'INVALID_STATE', 'errors': [str(exc)]}, ensure_ascii=False))
        return 2
    result = audit(record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] == 'INVALID_STATE' else 0


if __name__ == '__main__':
    sys.exit(main())
