"""Deterministic differential test of Task Lifecycle v0.1 against an independent state model.

The model is test-only and does not call the implementation's transition or
replay helpers. It is not an independent human review or a formal proof.
"""

from collections import Counter
from copy import deepcopy
import random
import unittest

from agent_state_contract import TaskContract

TYPES={'task.create':'TaskCreated','task.claim':'TaskClaimed','task.release':'TaskReleased','task.complete':'TaskCompleted'}

class Model:
    def __init__(self):
        self.states={}
        self.receipts={}
        self.events=[]
    def execute(self, c):
        bad={'ok':False,'code':'INVALID_COMMAND'}
        if not isinstance(c,dict) or not isinstance(c.get('type'),str) or c.get('type') not in TYPES:return bad
        k=c['type']; create=k=='task.create'
        required={'command_id','actor_id','type','task_id','payload'}| (set() if create else {'expected_version'})
        if set(c)!=required:return bad
        if any(not isinstance(c[n],str) or not c[n].strip() for n in ('command_id','actor_id','task_id')):return bad
        if not create and (type(c['expected_version']) is not int or c['expected_version']<1):return bad
        if not isinstance(c['payload'],dict):return bad
        if create and (set(c['payload'])!={'title'} or not isinstance(c['payload']['title'],str) or not c['payload']['title'].strip()):return bad
        if not create and c['payload']!={}:return bad
        receipt=self.receipts.get(c['command_id'])
        if receipt:
            old,first=receipt
            if old!=c:return {'ok':False,'code':'COMMAND_ID_REUSED'}
            return {**first,'applied':False}
        state=self.states.get(c['task_id']); actor=c['actor_id']; task_id=c['task_id']
        if create:
            if state:return {'ok':False,'code':'TASK_ALREADY_EXISTS'}
            self.states[task_id]={'task_id':task_id,'title':c['payload']['title'],'status':'todo','owner_agent_id':None,'version':1}
            version=1
        else:
            if not state:return {'ok':False,'code':'TASK_NOT_FOUND'}
            if c['expected_version']!=state['version']:
                return {'ok':False,'code':'VERSION_CONFLICT','current_version':state['version']}
            if k=='task.claim':
                if state['status']!='todo':return {'ok':False,'code':'INVALID_TRANSITION'}
                state['status']='in_progress';state['owner_agent_id']=actor
            else:
                if state['status']!='in_progress':return {'ok':False,'code':'INVALID_TRANSITION'}
                if state['owner_agent_id']!=actor:return {'ok':False,'code':'NOT_OWNER'}
                state['status']='todo' if k=='task.release' else 'done';state['owner_agent_id']=None
            state['version']+=1;version=state['version']
        result={'ok':True,'applied':True,'command_id':c['command_id'],'task_id':task_id,'version':version,'event_type':TYPES[k]}
        self.receipts[c['command_id']]=(deepcopy(c),deepcopy(result))
        self.events.append((task_id,c['command_id'],version))
        return result


class DifferentialModelTests(unittest.TestCase):
    def test_25_seed_differential_audit(self):
        cases=0
        coverage=Counter()
        for seed in range(25):
            rng=random.Random(seed*1847+42)
            model=Model();implementation=TaskContract();accepted=[]
            for i in range(375):
                # Keep live tasks in play: a static set becomes terminal quickly,
                # leaving almost every later command as a rejection or duplicate.
                cmdid=f's{seed}-c{i}'
                roll=rng.random()
                live=[state for state in model.states.values() if state['status']!='done']
                if roll < 0.57:
                    if not live or rng.random() < 0.24:
                        c={'command_id':cmdid,'actor_id':rng.choice(['agent-a','agent-b','agent-c']),
                           'task_id':f'new-{seed}-{i}','type':'task.create',
                           'payload':{'title':f'Task {seed}-{i}'}}
                    else:
                        state=rng.choice(live)
                        if state['status']=='todo':
                            kind='task.claim'
                            actor=rng.choice(['agent-a','agent-b','agent-c'])
                        else:
                            kind=rng.choice(['task.release','task.release','task.complete'])
                            actor=state['owner_agent_id']
                        c={'command_id':cmdid,'actor_id':actor,'task_id':state['task_id'],
                           'type':kind,'expected_version':state['version'],'payload':{}}
                elif roll < 0.69 and accepted:
                    c=deepcopy(rng.choice(accepted))
                elif roll < 0.80 and accepted:
                    c=deepcopy(rng.choice(accepted))
                    c['actor_id']='different-actor'
                elif roll < 0.96:
                    if model.states:
                        state=rng.choice(list(model.states.values()))
                        typ=rng.choice(['task.claim','task.release','task.complete','task.create'])
                        c={'command_id':cmdid,'actor_id':rng.choice(['agent-a','agent-b','agent-c']),
                           'task_id':state['task_id'],'type':typ,
                           'payload':{'title':'Duplicate title'} if typ=='task.create' else {}}
                        if typ!='task.create':
                            c['expected_version']=rng.choice([state['version'],max(1,state['version']-1),
                                                              state['version']+1])
                    else:
                        c={'command_id':cmdid,'actor_id':'agent-a',
                           'task_id':'not-found','type':'task.claim',
                           'expected_version':1,'payload':{}}
                else:
                    c={'command_id':cmdid,'actor_id':'agent-a','task_id':'malformed',
                       'type':'task.claim','expected_version':True,'payload':{}}
                expected=model.execute(c)
                observed=implementation.execute(deepcopy(c))
                if observed!=expected:raise AssertionError(f'case {seed}:{i}: {c}\nexpected {expected}\nobserved {observed}')
                if expected['ok'] and expected['applied']:
                    coverage['applied'] += 1
                    coverage[c['type']] += 1
                    accepted.append(deepcopy(c))
                elif expected['ok']:
                    coverage['duplicate'] += 1
                else:
                    coverage[expected['code']] += 1
                if len(implementation.events)!=len(model.events):raise AssertionError('unexpected events')
                # Check the changed task every time; inspect every task
                # periodically so an unrelated mutation cannot be missed.
                checked=list(model.states) if i%25==0 else [c['task_id']]
                checked.append('unseen-task')
                for t in checked:
                    result=implementation.get(t)
                    expectation=({'ok':True,'task':model.states[t]} if t in model.states else {'ok':False,'code':'TASK_NOT_FOUND'})
                    if result!=expectation:raise AssertionError((seed,i,t,result,expectation))
                cases+=1
        self.assertEqual(cases, 9_375)
        self.assertGreaterEqual(coverage['applied'], 3_000, coverage)
        self.assertGreaterEqual(coverage['task.release'], 350, coverage)
        self.assertGreaterEqual(coverage['task.complete'], 350, coverage)
        self.assertGreaterEqual(coverage['duplicate'], 600, coverage)
        for error in ('INVALID_COMMAND','COMMAND_ID_REUSED','VERSION_CONFLICT',
                      'INVALID_TRANSITION','NOT_OWNER','TASK_ALREADY_EXISTS','TASK_NOT_FOUND'):
            self.assertGreater(coverage[error], 0, (error, coverage))


if __name__ == "__main__":
    unittest.main()
