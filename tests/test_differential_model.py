"""Deterministic differential test of Task Lifecycle v0.1 against an independent state model.

The model is test-only and does not call the implementation's transition or
replay helpers. It is not an independent human review or a formal proof.
"""

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
        for seed in range(25):
            rng=random.Random(seed*1847+42)
            model=Model();implementation=TaskContract();accepted=[];rejected=[]
            for i in range(375):
                task=rng.choice(['t1','t2','t3','t4','t5'])
                actor=rng.choice(['agent-a','agent-b','agent-c'])
                typ=rng.choice(tuple(TYPES))
                version=model.states.get(task,{}).get('version',1)
                version=rng.choice([version,version,version+1,max(1,version-1),0,True,'1',None])
                cmdid=f's{seed}-c{i}'
                if accepted and rng.random()<0.19:
                    c=deepcopy(rng.choice(accepted))
                elif accepted and rng.random()<0.15:
                    c=deepcopy(rng.choice(accepted))
                    c[rng.choice(['actor_id','task_id','type'])]=rng.choice(['agent-z','tX','task.release'])
                elif rejected and rng.random()<0.08:
                    c=deepcopy(rng.choice(rejected));c['command_id']=cmdid
                else:
                    c={'command_id':cmdid,'actor_id':actor,'task_id':task,'type':typ,
                    'payload':{'title':rng.choice(['Title','  whitespace  ',''])} if typ=='task.create' else {},}
                    if typ!='task.create':c['expected_version']=version
                    if rng.random()<0.05:c['unexpected']=1
                before=len(model.events)
                expected=model.execute(c)
                observed=implementation.execute(deepcopy(c))
                if observed!=expected:raise AssertionError(f'case {seed}:{i}: {c}\nexpected {expected}\nobserved {observed}')
                if expected['ok'] and expected['applied']:accepted.append(c)
                else:rejected.append(c)
                if len(implementation.events)!=len(model.events):raise AssertionError('unexpected events')
                for t in ('t1','t2','t3','t4','t5'):
                    result=implementation.get(t)
                    expectation=({'ok':True,'task':model.states[t]} if t in model.states else {'ok':False,'code':'TASK_NOT_FOUND'})
                    if result!=expectation:raise AssertionError((seed,i,t,result,expectation))
                cases+=1
        self.assertEqual(cases, 9_375)


if __name__ == "__main__":
    unittest.main()
