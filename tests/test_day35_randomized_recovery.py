"""Seeded state transitions for one offline sender/receiver operation."""
from dataclasses import replace
import os
import random
from tempfile import TemporaryDirectory
import unittest

from day32_delivery import OfflineTransport
from tests import test_day34_recovery_model as recovery


SEEDS = range(3500, 3564)
OTHER_RECIPIENT = 'owner:bob'


class ChangedRecipientTransport(OfflineTransport):
    def frames(self, message):
        return (replace(message, recipient=OTHER_RECIPIENT),)


class RandomizedRecoveryTests(recovery.RecoveryModelHarness, unittest.TestCase):
    def next_action(self, rng):
        model = self.model
        times = [999, 1000, 1039, 1040, rng.randint(1000, 1042)]
        if model.status is not None:
            times.extend((model.last_time - 1, model.last_time, model.last_time + 1))
        if model.attempts:
            times.extend((model.deadline - 1, model.deadline, model.deadline + 1))
        now = rng.choice(times)
        actions = [('enqueue', now), ('claim', now), ('restart',),
                   ('attempt', rng.choice(tuple(recovery.ATTEMPTS)), now),
                   ('changed_recipient_frame', now),
                   ('update', rng.choice(('original', 'revoked')))]
        # The Day 34 oracle models a changed grant for an existing intent only.
        if model.status is not None:
            actions.append(('update', 'changed'))
        if model.attempts:
            generation = rng.randint(1, model.attempts)
            actions.extend((
                ('acknowledge', generation, now),
                ('wrong_token', generation, now),
                ('receive', generation, 23),
                ('wrong_recipient', generation),
            ))
            if model.effect is not None:
                actions.append(('receive', generation, 24))
        return rng.choice(actions)

    def opening(self, seed, rng):
        now = rng.randint(1000, 1005)
        # Force some traces through rarely reached states before random exploration.
        if seed % 4 == 0:
            return [
                ('enqueue', now),
                ('attempt', rng.choice(('outage', 'lost_ack')), now),
                ('restart',),
                ('attempt', 'outage', now + 5),
                ('attempt', 'outage', now + 10),
                ('attempt', 'normal', now + 15),
            ]
        if seed % 4 == 1:
            return [
                ('enqueue', now), ('attempt', 'lost_ack', now),
                ('update', 'revoked'), ('restart',), ('attempt', 'normal', now + 5),
                ('update', 'changed'), ('restart',), ('attempt', 'normal', now + 5),
                ('update', 'original'), ('claim', now + 5),
                ('acknowledge', 1, now + 5), ('wrong_token', 2, now + 5),
                ('wrong_recipient', 2), ('receive', 2, 24),
                ('receive', 2, 23), ('acknowledge', 2, now + 5),
                ('claim', now + 10),
            ]
        if seed % 4 == 2:
            return [
                ('enqueue', now), ('changed_recipient_frame', now),
                ('attempt', 'changed_frame', now + 5),
                ('attempt', 'duplicate', now + 10),
            ]
        return []

    def run_action(self, action):
        name, *args = action
        if name == 'wrong_token':
            self.acknowledge(*args, wrong_token=True)
        elif name == 'wrong_recipient':
            self.receive(*args, 23, recipient=OTHER_RECIPIENT)
        elif name == 'changed_recipient_frame':
            self.attempt('changed_frame', *args, transport=ChangedRecipientTransport())
        else:
            getattr(self, name)(*args)

    def run_sequence(self, seed, trace):
        rng = random.Random(seed)
        opening = self.opening(seed, rng)
        length = rng.randint(20, 55)
        with TemporaryDirectory() as directory:
            self.provision(directory)
            for step in range(length):
                action = opening[step] if step < len(opening) else self.next_action(rng)
                trace.append(action)
                self.run_action(action)

    def test_seeded_sequences(self):
        selected = os.environ.get('DAY35_SEED')
        seeds = (int(selected),) if selected is not None else SEEDS
        for seed in seeds:
            with self.subTest(seed=seed):
                trace = []
                try:
                    self.run_sequence(seed, trace)
                except Exception as error:
                    replay = f'DAY35_SEED={seed} python -m unittest {__name__}'
                    error.add_note(f'Seed {seed}, step {len(trace)}. Replay with {replay}\n'
                                   f'Actions through failure: {trace!r}')
                    raise
