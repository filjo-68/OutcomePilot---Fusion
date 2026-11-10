"""67 distinct sequential adversarial test vectors; fixtures are synthetic, not live agent E2E.

Each vector independently mutates a clean record and checks its terminal classification.
"""
import copy
import importlib.util
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[2] / 'skills' / 'outcomepilot-fusion' / 'scripts' / 'record_audit.py'
spec = importlib.util.spec_from_file_location('fusion_record_audit', source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fresh():
    return {
        'objective': 'Deliver reviewed artifact', 'max_steps': 10, 'used_steps': 3,
        'criteria': [{'id': 'C1', 'required': True, 'status': 'PASS', 'evidence_ids': ['E1']}],
        'evidence': [{'id': 'E1', 'kind': 'FILE_CHECK', 'check_result': 'PASS',
                      'source': 'illustrative opened file', 'criterion_ids': ['C1']}],
        'actions': [{'id': 'A1', 'kind': 'LOCAL_EDIT', 'status': 'DONE', 'target': 'local file',
                     'authorization': 'NOT_REQUIRED', 'receipt_evidence_ids': [],
                     'postcondition_evidence_ids': [], 'ambiguous': False, 'reconciled': True}],
    }


def e2(kind='READ_BACK', status='PASS'):
    return {'id': 'E2', 'kind': kind, 'check_result': status, 'source': 'illustrative provider readback', 'criterion_ids': []}


def ext(r):
    r['evidence'].append(e2())
    r['actions'][0].update(kind='EXTERNAL_WRITE', authorization='HOST_CONFIRMED',
                           receipt_evidence_ids=['E1'], postcondition_evidence_ids=['E2'])


def partial(r):
    r['criteria'].append({'id': 'C2', 'required': True, 'status': 'NOT_RUN', 'evidence_ids': []})
    r['useful_partial'] = True


def unknown_write(r):
    ext(r)
    r['actions'][0].update(status='UNKNOWN', ambiguous=True, reconciled=False)


# Tests deliberately isolate one contract or failure mode per step.
CASES = []
def case(name, expected, mutate, match=None):
    CASES.append((name, expected, mutate, match))

case('clean_record_complete', 'RECORDED_COMPLETE', lambda r: None)
case('wrong_top_type', 'INVALID_STATE', lambda r: None, 'Record must be an object')
case('missing_objective', 'INVALID_STATE', lambda r: r.pop('objective'))
case('blank_objective', 'INVALID_STATE', lambda r: r.update(objective='  '))
case('bool_max_steps', 'INVALID_STATE', lambda r: r.update(max_steps=True))
case('bool_used_steps', 'INVALID_STATE', lambda r: r.update(used_steps=False))
case('negative_used_steps', 'INVALID_STATE', lambda r: r.update(used_steps=-1))
case('zero_max_steps', 'INVALID_STATE', lambda r: r.update(max_steps=0))
case('over_budget_step_counter', 'INVALID_STATE', lambda r: r.update(used_steps=11))
case('unknown_record_field', 'INVALID_STATE', lambda r: r.update(secret_state='PASS'))
case('null_criteria', 'INVALID_STATE', lambda r: r.update(criteria=None))
case('empty_criteria', 'INVALID_STATE', lambda r: r.update(criteria=[]))
case('non_object_criterion', 'INVALID_STATE', lambda r: r.update(criteria=[7]))
case('duplicate_criterion', 'INVALID_STATE', lambda r: r['criteria'].append(copy.deepcopy(r['criteria'][0])))
case('blank_criterion_id', 'INVALID_STATE', lambda r: r['criteria'][0].update(id='  '))
case('string_required', 'INVALID_STATE', lambda r: r['criteria'][0].update(required='true'))
case('criterion_unknown_state', 'INVALID_STATE', lambda r: r['criteria'][0].update(status='PROVED'))
case('null_criterion_links', 'INVALID_STATE', lambda r: r['criteria'][0].update(evidence_ids=None))
case('duplicate_criterion_links', 'INVALID_STATE', lambda r: r['criteria'][0].update(evidence_ids=['E1','E1']))
case('unknown_criterion_field', 'INVALID_STATE', lambda r: r['criteria'][0].update(user_score=100))
case('null_evidence', 'INVALID_STATE', lambda r: r.update(evidence=None))
case('non_object_evidence', 'INVALID_STATE', lambda r: r.update(evidence=['evidence']))
case('duplicate_evidence_id', 'INVALID_STATE', lambda r: r['evidence'].append(copy.deepcopy(r['evidence'][0])))
case('blank_evidence_source', 'INVALID_STATE', lambda r: r['evidence'][0].update(source='\n'))
case('invalid_evidence_kind', 'INVALID_STATE', lambda r: r['evidence'][0].update(kind='FAKE'))
case('invalid_check_result', 'INVALID_STATE', lambda r: r['evidence'][0].update(check_result='SUCCESS'))
case('null_evidence_links', 'INVALID_STATE', lambda r: r['evidence'][0].update(criterion_ids=None))
case('duplicate_evidence_links', 'INVALID_STATE', lambda r: r['evidence'][0].update(criterion_ids=['C1','C1']))
case('unknown_evidence_field', 'INVALID_STATE', lambda r: r['evidence'][0].update(truth=1))
case('nonreciprocal_evidence_link', 'INVALID_STATE', lambda r: r['evidence'][0].update(criterion_ids=[]))
case('passing_claim_on_failed_evidence', 'INVALID_STATE', lambda r: r['evidence'][0].update(check_result='FAIL'))

def contradictory(r):
    r['evidence'].append({'id':'E2','kind':'OTHER','check_result':'FAIL','source':'independent contrary fixture','criterion_ids':['C1']})
    r['criteria'][0]['evidence_ids'].append('E2')
case('unresolved_failed_counterevidence', 'INVALID_STATE', contradictory)
case('orphan_criterion_reference', 'INVALID_STATE', lambda r: r['evidence'][0].update(criterion_ids=['C9']))
case('missing_evidence_id', 'INVALID_STATE', lambda r: r['criteria'][0].update(evidence_ids=['MISSING']))
case('all_optional_criteria', 'INVALID_STATE', lambda r: r['criteria'][0].update(required=False))
case('null_actions', 'INVALID_STATE', lambda r: r.update(actions=None))
case('non_object_action', 'INVALID_STATE', lambda r: r.update(actions=['bad']))
case('duplicate_action', 'INVALID_STATE', lambda r: r['actions'].append(copy.deepcopy(r['actions'][0])))
case('invalid_action_kind', 'INVALID_STATE', lambda r: r['actions'][0].update(kind='PURCHASE'))
case('invalid_action_state', 'INVALID_STATE', lambda r: r['actions'][0].update(status='SUCCESS'))
case('invalid_action_authorization', 'INVALID_STATE', lambda r: r['actions'][0].update(authorization='YES'))
case('blank_action_target', 'INVALID_STATE', lambda r: r['actions'][0].update(target='  '))
case('ambiguous_flag_as_string', 'INVALID_STATE', lambda r: r['actions'][0].update(ambiguous='false'))
case('null_receipts_array', 'INVALID_STATE', lambda r: r['actions'][0].update(receipt_evidence_ids=None))
case('null_postcondition_array', 'INVALID_STATE', lambda r: r['actions'][0].update(postcondition_evidence_ids=None))

def ext_unapproved(r): ext(r); r['actions'][0]['authorization'] = 'CLAIMED_APPROVED'
case('external_done_unapproved', 'INVALID_STATE', ext_unapproved)

def ext_no_receipt(r): ext(r); r['actions'][0]['receipt_evidence_ids'] = []
case('external_done_missing_receipt', 'INVALID_STATE', ext_no_receipt)

def ext_no_post(r): ext(r); r['actions'][0]['postcondition_evidence_ids'] = []
case('external_done_missing_post', 'INVALID_STATE', ext_no_post)

def ext_reuse_receipt(r): ext(r); r['actions'][0]['postcondition_evidence_ids'] = ['E1']
case('receipt_reused_as_postcondition', 'INVALID_STATE', ext_reuse_receipt)
case('external_done_separate_readback', 'RECORDED_COMPLETE', ext)
case('unknown_external_write_blocks', 'BLOCKED', unknown_write)

def unknown_without_flag(r): ext(r); r['actions'][0].update(status='UNKNOWN', ambiguous=False)
case('unknown_external_write_even_without_flag', 'BLOCKED', unknown_without_flag)

def ambiguous_done(r): ext(r); r['actions'][0].update(ambiguous=True, reconciled=False)
case('unreconciled_done_invalid', 'INVALID_STATE', ambiguous_done)

def pending_approval(r): r['criteria'][0]['status']='NOT_RUN'; r['actions'][0].update(kind='EXTERNAL_WRITE', status='PLANNED', authorization='REQUIRED_PENDING')
case('pending_authorization_stops', 'APPROVAL_REQUIRED', pending_approval)
case('cancelled_priority', 'CANCELLED', lambda r: r.update(cancelled=True))
case('unsafe_priority', 'UNSAFE', lambda r: r.update(unsafe=True))
case('unregistered_next_step', 'INVALID_STATE', lambda r: r.update(next_action_id='NO'))
case('next_step_must_be_planned', 'INVALID_STATE', lambda r: r.update(next_action_id='A1'))
case('usable_required_partial', 'RECORDED_PARTIAL', partial)

def no_required_partial(r): partial(r); r['criteria'][0]['required']=False
case('optional_pass_is_not_partial', 'BLOCKED', no_required_partial)

def budget_exhausted(r): r['criteria'][0]['status']='NOT_RUN'; r['used_steps']=10
case('hard_budget_exhausted', 'BUDGET_EXHAUSTED', budget_exhausted)

def next_safe_action(r): r['criteria'][0]['status']='NOT_RUN'; r['actions'][0]['status']='PLANNED'; r['next_action_id']='A1'
case('registered_next_safe_action', 'WORK_REMAINING', next_safe_action)

def passing_optional_without_required(r): r['criteria'][0]['required']=False; r['criteria'].append({'id':'C2','required':True,'status':'NOT_RUN','evidence_ids':[]})
case('required_not_run_not_complete', 'BLOCKED', passing_optional_without_required)

def bad_reconciliation(r): ext(r); r['actions'][0].update(status='UNKNOWN', ambiguous=True, reconciled=True)
case('unknown_even_if_reconciled_claimed', 'BLOCKED', bad_reconciliation)

def post_wrong_kind(r): ext(r); r['evidence'][1]['kind']='SOURCE_CHECK'
case('source_check_not_external_postcondition', 'INVALID_STATE', post_wrong_kind)

def post_failed(r): ext(r); r['evidence'][1]['check_result']='FAIL'
case('failed_postcondition_not_done', 'INVALID_STATE', post_failed)


def done_with_pending_approval(r):
    r['actions'][0]['authorization'] = 'REQUIRED_PENDING'
case('pending_approval_cannot_be_done', 'INVALID_STATE', done_with_pending_approval)

assert len(CASES) == 67, len(CASES)


class SequentialAuditCycles(unittest.TestCase):
    pass


def make_test(number, name, expect, mutation, match):
    def test(self):
        rec = None if number == 2 else fresh()
        if rec is not None:
            mutation(rec)
        result = mod.audit(rec)
        self.assertEqual(result['status'], expect, f'Iteration {number:02d} {name}: {result}')
        if match:
            self.assertIn(match, ' '.join(result.get('errors', [])))
    return test


for i, (name, expect, mutation, match) in enumerate(CASES, 1):
    setattr(SequentialAuditCycles, f'test_{i:02d}_{name}', make_test(i, name, expect, mutation, match))


if __name__ == '__main__':
    unittest.main()
