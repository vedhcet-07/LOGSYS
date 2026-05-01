import sys
sys.path.insert(0, 'backend')
#test2
print('--- Phase 2 Import Test ---')
from agents.base_agent import BaseAgent
print('[OK] base_agent')
from agents.retrieval_agent import RetrievalAgent
print('[OK] retrieval_agent')
from agents.rca_agent import RCAAgent
print('[OK] rca_agent')
from agents.orchestrator import Orchestrator
print('[OK] orchestrator')
from api.routes import router
print('[OK] routes wired')

print()
print('--- Unit: RetrievalAgent (demo fallback) ---')
from services.graph_store import load_graph
load_graph()

agent = RetrievalAgent()
result = agent.run({'query': 'Why did auth-service fail?'})
n_ev   = len(result['evidence'])
n_gr   = len(result['graph_nodes'])
n_tr   = len(result['trace'])
print('Evidence items:', n_ev)
print('Graph nodes   :', n_gr)
print('Trace events  :', n_tr)
for t in result['trace']:
    print('  [' + t['agent'] + ']', t['action'], '->', t['result'][:60])

print()
print('--- Unit: RCAAgent (template fallback) ---')
rca = RCAAgent()
rca_result = rca.run({
    'query': 'Why did auth-service fail?',
    'evidence': result['evidence'],
    'graph_nodes': result['graph_nodes'],
})
out = rca_result['rca']
print('Root cause:', out.root_cause[:80])
print('Confidence:', out.confidence)
print('Services  :', out.affected_services[:3])
print('Recs      :', len(out.recommendations))
print('Evidence  :', len(out.evidence))
print('Trace evts:', len(rca_result['trace']))

print()
print('--- Unit: Full Orchestrator ---')
orch = Orchestrator()
final = orch.run('Why did auth-service fail around 2:31 AM?')
print('Answer (100):', final.answer[:100])
print('Confidence  :', final.confidence)
print('Trace events:', len(final.agent_trace))
for t in final.agent_trace:
    print('  [' + t['agent'] + ']', t['action'])

print()
print('PHASE 2 SMOKE TEST: PASSED')
