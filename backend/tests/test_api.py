import os
import tempfile
from pathlib import Path

tmp = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tmp.name)/'test.db')
from fastapi.testclient import TestClient
from app.main import app
import pytest
from app.database import engine

@pytest.fixture(scope='session',autouse=True)
def cleanup():
    yield
    engine.dispose()
    tmp.cleanup()

def test_catalog_and_recommendation_constraints():
    with TestClient(app) as client:
        assert client.get('/api/products').json()['total']==600
        original=client.get('/api/products/1').json()
        response=client.post('/api/substitutes',json={'product_id':1,'max_price_deviation':0.4,'limit':0})
        assert response.status_code==200
        rows=response.json()['results']
        assert rows
        assert [r['score'] for r in rows]==sorted([r['score'] for r in rows],reverse=True)
        for row in rows:
            p=row['product']
            assert p['product_id']!=1 and p['stock_quantity']>0 and p['status']=='active'
            assert p['subcategory']==original['subcategory'] and p['specifications']==original['specifications']
            assert abs(p['price']-original['price'])/original['price']<=.4
            assert 0<=row['score']<=100
        none=client.post('/api/substitutes',json={'product_id':1,'required_specs':{'connector':'impossible'}}).json()
        assert none['eligible_count']==0 and none['message']

def test_import_atomicity_and_settings():
    with TestClient(app) as client:
        before=client.get('/api/products').json()['total']
        bad=client.post('/api/products/import',files={'file':('bad.csv',b'product_name,sku\nBroken,new\n','text/csv')})
        assert bad.status_code==422
        assert client.get('/api/products').json()['total']==before
        assert client.put('/api/settings',json={'attribute':10}).status_code==422
        saved=client.put('/api/settings',json={'attribute':40,'semantic':15,'category':15,'price':15,'availability':10,'brand':5})
        assert saved.status_code==200
        assert client.get('/api/settings').json()['weights']['attribute']==40

def test_crud_graph_and_delete_safeguard():
    with TestClient(app) as client:
        payload={'product_name':'Test unique item','sku':'TEST-UNIQUE','brand':'Test','category':'Test category','subcategory':'Test sub','price':10,'cost':5,'supplier_id':'SUP-TEST','specifications':{'safe':True},'stock_quantity':10}
        created=client.post('/api/products',json=payload)
        assert created.status_code==201
        pid=created.json()['product_id']
        assert client.post('/api/products',json=payload).status_code==409
        graph=client.get(f'/api/graph/{pid}').json()
        assert any(n['label']=='Test category' for n in graph['nodes'])
        payload['price']=12
        assert client.put(f'/api/products/{pid}',json=payload).json()['price']==12
        assert client.delete(f'/api/products/{pid}?confirm_sku=wrong').status_code==409
        assert client.delete(f'/api/products/{pid}?confirm_sku=TEST-UNIQUE').status_code==200
        assert client.get(f'/api/products/{pid}').status_code==404

def test_optimizer_feasibility_and_evidence():
    with TestClient(app) as client:
        result=client.post('/api/optimize',json={'budget':100,'max_products':10,'min_per_category':1}).json()
        assert result['status']=='Optimal'
        assert result['total_cost']<=100.01
        assert len(result['products'])<=10 and result['categories_covered']==5
        bad=client.post('/api/optimize',json={'budget':.01,'max_products':1,'min_per_category':1}).json()
        assert bad['status']=='Infeasible' and not bad['products']
        answer=client.post('/api/ask',json={'question':'oat milk'}).json()
        assert answer['mode']=='deterministic' and answer['evidence_ids']
        assert set(answer['evidence_ids'])=={p['product_id'] for p in answer['evidence']}
