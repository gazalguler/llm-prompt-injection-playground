"""Offline sealed-evidence mutation checks; never execute model requests."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

import day23_review as review


@unittest.skipUnless(review.RUN.is_dir(), 'Private Day 23 raw archive required for local-only verification')
class Day23ReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        shutil.copytree(review.RUN, root/'run')
        shutil.copytree(review.REVIEW, root/'review')
        for obj, key, value in ((review, 'RUN', root/'run'), (review, 'REVIEW', root/'review'),
                                (socket, 'socket', unittest.mock.Mock(side_effect=AssertionError('network forbidden')))):
            item = patch.object(obj, key, value)
            item.start(); self.addCleanup(item.stop)

    def rewrite(self, path, value):
        path.write_text(json.dumps(value))

    def reseal(self):
        # Deliberately recompute checksums to test semantic links, not just hashes.
        manifest = review.read(review.RUN/'SHA256SUMS.json')
        for name in manifest:
            manifest[name] = review.sha(review.RUN/name)
        self.rewrite(review.RUN/'SHA256SUMS.json', manifest)
        stage = review.read(review.REVIEW/'review_stage.json')
        stage['run_manifest_sha256'] = review.sha(review.RUN/'SHA256SUMS.json')
        stage['reviews_sha256'] = review.sha(review.REVIEW/'reviews.json')
        self.rewrite(review.REVIEW/'review_stage.json', stage)

    def test_exact_evidence_and_separate_metrics(self):
        result = review.analyze()
        expected = review.read(review.RESULT)
        self.assertEqual(result, expected)
        self.assertEqual(result['model_level']['resistance'], review.metric(0,4))
        self.assertEqual(result['model_level']['full_success'], review.metric(2,4))
        self.assertEqual(result['model_level']['partial_compliance'], review.metric(2,4))
        self.assertEqual(result['model_level']['factual_task_completion'], review.metric(6,8))
        self.assertEqual(result['model_level']['core_facts_present'], review.metric(7,8))
        self.assertEqual(result['gates']['day22']['false_blocks'], review.metric(3,3))
        self.assertEqual(result['gates']['day22']['clean_control_release'], review.metric(0,4))
        self.assertEqual(result['gates']['day22']['compromised_attack_outputs_blocked'], review.metric(4,4))

    def test_changed_raw_bytes_rejected(self):
        with (review.RUN/'response_01.raw.json').open('ab') as stream:
            stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            review.analyze()

    def test_missing_and_extra_files_rejected(self):
        path = review.RUN/'unexpected.json'; path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            review.analyze()
        path.unlink()
        (review.RUN/'response_08.attempt.json').unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            review.analyze()

    def test_semantic_tampering_rejected_even_with_recomputed_hashes(self):
        originals = {p:p.read_bytes() for folder in (review.RUN, review.REVIEW) for p in folder.rglob('*') if p.is_file()}
        for mutation in ('attempt','gate','model','complete','source','plan','review_link','review_type','review_identity'):
            with self.subTest(mutation=mutation):
                for path, raw in originals.items():
                    path.write_bytes(raw)
                if mutation=='attempt':
                    path=review.RUN/'response_01.attempt.json';value=review.read(path);value['request_sha256']='0'*64;self.rewrite(path,value)
                elif mutation=='gate':
                    path=review.RUN/'response_01.gate.json';value=review.read(path);value['decisions']['day22']['released']=True;self.rewrite(path,value)
                elif mutation=='model':
                    path=review.RUN/'tags.raw.json';value=review.read(path)
                    for model in value['models']:
                        if model['name']==review.frozen.transport.MODEL:model['digest']='0'*64
                    self.rewrite(path,value)
                elif mutation=='complete':
                    self.rewrite(review.RUN/'complete.json',dict(attempted=9,completed=8,retries=1))
                elif mutation=='source':
                    (review.RUN/'sources/day22_gate.py').write_text('changed')
                elif mutation=='plan':
                    path=review.RUN/'plan.json';value=review.read(path);value['requests'][0]['facts']['duration']=48;self.rewrite(path,value)
                else:
                    path=review.REVIEW/'reviews.json';value=review.read(path)
                    if mutation=='review_link':value[0]['raw_sha256']='0'*64
                    if mutation=='review_type':value[0]['task_completed']='true'
                    if mutation=='review_identity':value[0]['trial_id']=value[1]['trial_id']
                    self.rewrite(path,value)
                self.reseal()
                with self.assertRaises(ValueError):
                    review.analyze()

    def test_saved_result_tampering_rejected_by_cli(self):
        path=review.REVIEW/'altered_results.json'
        value=review.read(review.RESULT);value['gates']['day22']['false_blocks']['numerator']=0
        self.rewrite(path,value)
        with patch.object(review,'RESULT',path),patch.object(sys,'argv',['day23_review.py','--check']),redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError,'Saved live results mismatch'):
                review.main()
