"""Optional LangGraph retrieval and evidence validation workflow."""
import os
from typing import TypedDict

class EvidenceState(TypedDict):
    question: str
    records: list[dict]
    evidence: list[dict]

def retrieve(state: EvidenceState):
    terms=state['question'].lower().split()
    scored=[]
    for record in state['records']:
        text=' '.join(str(record.get(k,'')) for k in ('product_name','category','subcategory','sku')).lower()
        score=sum(term in text for term in terms)
        if score: scored.append((score,record))
    scored.sort(key=lambda entry:(-entry[0],entry[1]['product_id']))
    return {'evidence':[record for _,record in scored[:8]]}

def validate(state: EvidenceState):
    ids={r['product_id'] for r in state['records']}
    if any(r['product_id'] not in ids for r in state['evidence']):
        raise ValueError('Retrieved evidence was not present in catalog')
    return {'evidence':state['evidence']}

def retrieve_evidence(question,records):
    state={'question':question,'records':records,'evidence':[]}
    if os.getenv('AI_ORCHESTRATION','direct')=='langgraph':
        from langgraph.graph import StateGraph, START, END
        graph=StateGraph(EvidenceState)
        graph.add_node('retrieve_catalog',retrieve)
        graph.add_node('validate_evidence',validate)
        graph.add_edge(START,'retrieve_catalog')
        graph.add_edge('retrieve_catalog','validate_evidence')
        graph.add_edge('validate_evidence',END)
        return graph.compile().invoke(state)['evidence']
    state.update(retrieve(state))
    return validate(state)['evidence']
