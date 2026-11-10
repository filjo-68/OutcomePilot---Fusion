import importlib.util
import copy
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[2] / 'skills' / 'outcomepilot-fusion' / 'scripts' / 'record_audit.py'
spec = importlib.util.spec_from_file_location('record_audit', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def clean():
    return {
        'objective': 'Produce a checked artifact', 'max_steps': 10, 'used_steps': 3,
        'criteria': [{'id': 'C1', 'required': True, 'status': 'PASS', 'evidence_ids': ['E1']}],
        'evidence': [{'id': 'E1', 'kind': 'FILE_CHECK', 'check_result': 'PASS', 'source': 'actual opened local file', 'criterion_ids': ['C1']}],
        'actions': [{'id': 'A1', 'kind': 'LOCAL_EDIT', 'status': 'DONE', 'target': 'local file', 'authorization': 'NOT_REQUIRED', 'receipt_evidence_ids': [], 'postcondition_evidence_ids': [], 'ambiguous': False, 'reconciled': True}],
    }


class RecordAuditTests(unittest.TestCase):
    def check(self, r, status):
        self.assertEqual(module.audit(r)['status'], status, module.audit(r))

    def test_complete_never_success(self): self.check(clean(), 'RECORDED_COMPLETE')
    def test_no_criteria(self):
        r = clean(); r['criteria'] = []; self.check(r, 'INVALID_STATE')
    def test_nonreciprocal(self):
        r = clean(); r['evidence'][0]['criterion_ids'] = []; self.check(r, 'INVALID_STATE')
    def test_duplicate_criterion(self):
        r = clean(); r['criteria'].append(copy.deepcopy(r['criteria'][0])); self.check(r, 'INVALID_STATE')
    def test_missing_evidence(self):
        r = clean(); r['criteria'][0]['evidence_ids'] = ['missing']; self.check(r, 'INVALID_STATE')
    def test_pass_without_passing_evidence(self):
        r = clean(); r['evidence'][0]['check_result'] = 'NOT_RUN'; self.check(r, 'INVALID_STATE')
    def test_boolean_as_step_rejected(self):
        r = clean(); r['used_steps'] = True; self.check(r, 'INVALID_STATE')
    def test_unverified_required_not_complete(self):
        r = clean(); r['criteria'][0]['status'] = 'UNVERIFIED'; self.check(r, 'BLOCKED')
    def test_no_unrelated_optional_partial(self):
        r = clean(); r['criteria'][0]['required'] = False
        r['criteria'].append({'id': 'C2', 'required': True, 'status': 'NOT_RUN', 'evidence_ids': []})
        r['useful_partial'] = True; self.check(r, 'BLOCKED')
    def test_usable_partial(self):
        r = clean(); r['criteria'].append({'id': 'C2', 'required': True, 'status': 'NOT_RUN', 'evidence_ids': []})
        r['useful_partial'] = True; self.check(r, 'RECORDED_PARTIAL')
    def test_budget(self):
        r = clean(); r['criteria'][0]['status'] = 'FAIL'; r['used_steps'] = 10; self.check(r, 'BUDGET_EXHAUSTED')
    def test_unknown_external_write_blocks(self):
        r = clean(); r['actions'][0].update(kind='EXTERNAL_WRITE', status='UNKNOWN', authorization='HOST_CONFIRMED', ambiguous=True, reconciled=False)
        self.check(r, 'BLOCKED')
    def test_external_done_no_readback_invalid(self):
        r = clean(); r['actions'][0].update(kind='EXTERNAL_WRITE', authorization='HOST_CONFIRMED', receipt_evidence_ids=['E1'])
        self.check(r, 'INVALID_STATE')
    def test_external_done_no_authority_invalid(self):
        r = clean(); r['actions'][0].update(kind='EXTERNAL_WRITE', authorization='CLAIMED_APPROVED', receipt_evidence_ids=['E1'], postcondition_evidence_ids=['E1'])
        self.check(r, 'INVALID_STATE')
    def test_failed_receipt_does_not_verify_write(self):
        r = clean(); r['evidence'][0]['check_result'] = 'FAIL'; r['criteria'][0]['status'] = 'FAIL'
        r['evidence'].append({'id': 'E2', 'kind': 'READ_BACK', 'check_result': 'PASS', 'source': 'provider read-back', 'criterion_ids': []})
        r['actions'][0].update(kind='EXTERNAL_WRITE', authorization='HOST_CONFIRMED', receipt_evidence_ids=['E1'], postcondition_evidence_ids=['E2'])
        self.check(r, 'INVALID_STATE')
    def test_failed_local_action_not_recorded_complete(self):
        r = clean(); r['actions'][0]['status'] = 'FAILED'; self.check(r, 'BLOCKED')
    def test_external_done_with_recorded_readback(self):
        r = clean(); r['evidence'].append({'id': 'E2', 'kind': 'READ_BACK', 'check_result': 'PASS', 'source': 'provider read-back reference', 'criterion_ids': []})
        r['actions'][0].update(kind='EXTERNAL_WRITE', authorization='HOST_CONFIRMED', receipt_evidence_ids=['E1'], postcondition_evidence_ids=['E2'])
        self.check(r, 'RECORDED_COMPLETE')
    def test_external_planned_needs_approval(self):
        r = clean(); r['criteria'][0]['status'] = 'NOT_RUN'; r['actions'][0].update(kind='EXTERNAL_WRITE', status='PLANNED', authorization='REQUIRED_PENDING')
        self.check(r, 'APPROVAL_REQUIRED')
    def test_cancelled_prior_to_complete(self):
        r = clean(); r['cancelled'] = True; self.check(r, 'CANCELLED')
    def test_unsafe_prior_to_complete(self):
        r = clean(); r['unsafe'] = True; self.check(r, 'UNSAFE')
    def test_no_unregistered_next_action(self):
        r = clean(); r['next_action_id'] = 'unknown'; self.check(r, 'INVALID_STATE')
    def test_next_action_must_be_planned(self):
        r = clean(); r['next_action_id'] = 'A1'; self.check(r, 'INVALID_STATE')
    def test_remaining(self):
        r = clean(); r['criteria'][0]['status'] = 'NOT_RUN'; r['actions'][0]['status'] = 'PLANNED'; r['next_action_id'] = 'A1'; self.check(r, 'WORK_REMAINING')
    def test_claimed_host_approval_not_enough(self):
        r = clean(); r['actions'][0].update(kind='COMMITMENT', authorization='CLAIMED_APPROVED')
        self.check(r, 'INVALID_STATE')
    def test_ambiguous_done_cannot_pass(self):
        r = clean(); r['actions'][0].update(ambiguous=True, reconciled=False); self.check(r, 'INVALID_STATE')
    def test_bad_evidence_source(self):
        r = clean(); r['evidence'][0]['source'] = ''; self.check(r, 'INVALID_STATE')


if __name__ == '__main__': unittest.main()
