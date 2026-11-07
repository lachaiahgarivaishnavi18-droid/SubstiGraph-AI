import os
import json
from pathlib import Path
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .database import serialize

def text_for(p):
    return ' '.join([p.product_name,p.description,p.category,p.subcategory,json.dumps(p.attributes),json.dumps(p.specifications)])

class Knowledge:
    def __init__(self):
        self.graph = nx.Graph()
        self.products = []
        self.semantic_mode = os.getenv('SEMANTIC_MODE','tfidf')
        self.backend = os.getenv('GRAPH_BACKEND','networkx')
        if self.backend not in ('networkx','neo4j'):
            raise ValueError('GRAPH_BACKEND must be networkx or neo4j')
        if self.semantic_mode not in ('tfidf','sentence-transformers'):
            raise ValueError('SEMANTIC_MODE must be tfidf or sentence-transformers')
        self.error = None

    def remote_query(self, query, **parameters):
        from neo4j import GraphDatabase
        with GraphDatabase.driver(os.environ['NEO4J_URI'],auth=(os.environ['NEO4J_USER'],os.environ['NEO4J_PASSWORD'])) as driver:
            with driver.session() as session:
                return session.run(query, **parameters).data()

    def rebuild(self, products):
        self.products = products
        self.graph = nx.Graph()
        texts = [text_for(p) for p in products]
        if not products:
            self.similarities = np.zeros((0,0))
        elif self.semantic_mode == 'sentence-transformers':
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(os.getenv('EMBEDDING_MODEL','all-MiniLM-L6-v2'))
            embeddings = model.encode(texts)
            Path('data').mkdir(exist_ok=True)
            np.save('data/embeddings.npy', embeddings)
            Path('data/embedding_ids.json').write_text(json.dumps([p.product_id for p in products]))
            self.similarities = cosine_similarity(embeddings)
        else:
            self.similarities = cosine_similarity(TfidfVectorizer(stop_words='english').fit_transform(texts))
        for p in products:
            pid = f'product:{p.product_id}'
            self.graph.add_node(pid, label=p.product_name, type='Product', product_id=p.product_id)
            entities = [('Category',p.category,'PRODUCT_BELONGS_TO_CATEGORY'),('Subcategory',p.subcategory,'PRODUCT_BELONGS_TO_SUBCATEGORY'),('Brand',p.brand,'PRODUCT_HAS_BRAND'),('Supplier',p.supplier_id,'PRODUCT_SUPPLIED_BY')]
            entities += [('Attribute',f'{k}: {v}','PRODUCT_HAS_ATTRIBUTE') for k,v in p.attributes.items()]
            entities += [('Feature',f'{k}: {v}','PRODUCT_HAS_FEATURE') for k,v in p.specifications.items()]
            for kind,label,relation in entities:
                node = f'{kind}:{label}'
                self.graph.add_node(node,label=label,type=kind)
                self.graph.add_edge(pid,node,relation=relation,relationship_source='product_record')
        for i,p in enumerate(products):
            candidates = [(j,q) for j,q in enumerate(products) if j>i and p.category==q.category and p.subcategory==q.subcategory and p.specifications==q.specifications]
            for j,q in candidates:
                similarity = float(self.similarities[i,j])
                self.graph.add_edge(f'product:{p.product_id}',f'product:{q.product_id}',relation='PRODUCT_SUBSTITUTE_FOR', similarity_score=round(similarity*100,2),price_difference=round(q.price-p.price,2),compatibility_score=100,availability_score=100 if q.stock_quantity else 0,relationship_source='exact_subcategory_and_specifications',confidence=1.0)
        self.error = None
        if self.backend == 'neo4j':
            try:
                from neo4j import GraphDatabase
                with GraphDatabase.driver(os.environ['NEO4J_URI'],auth=(os.environ['NEO4J_USER'],os.environ['NEO4J_PASSWORD'])) as driver:
                    driver.verify_connectivity()
                    # All mirrored entities are namespaced; unrelated Neo4j data is untouched.
                    nodes=[{'id':n,**d} for n,d in self.graph.nodes(data=True)]
                    edges=[{'source':a,'target':b,**d} for a,b,d in self.graph.edges(data=True)]
                    def sync(tx):
                        tx.run('MATCH (n:SubstiGraph) DETACH DELETE n').consume()
                        tx.run('UNWIND $nodes AS row CREATE (n:SubstiGraph {id: row.id}) SET n += row',nodes=nodes).consume()
                        for relation in sorted({e['relation'] for e in edges}):
                            # Relation names are exclusively internal constants.
                            tx.run(f'UNWIND $edges AS row MATCH (a:SubstiGraph {{id: row.source}}), (b:SubstiGraph {{id: row.target}}) CREATE (a)-[r:{relation}]->(b) SET r += row',edges=[e for e in edges if e['relation']==relation]).consume()
                    with driver.session() as session:
                        session.execute_write(sync)
            except Exception as exc:
                self.error = f'Neo4j synchronization failed: {type(exc).__name__}. Local graph remains available.'

    def neighborhood(self, product_id):
        node = f'product:{product_id}'
        if self.backend=='neo4j' and not self.error:
            try:
                rows=self.remote_query('MATCH (a:SubstiGraph {id: $id})-[r]-(b:SubstiGraph) RETURN properties(a) AS source, properties(b) AS target, properties(r) AS edge LIMIT 60',id=node)
                nodes={}; edges=[]
                for row in rows:
                    nodes[row['source']['id']]=row['source']; nodes[row['target']['id']]=row['target']
                    edges.append({**row['edge'],'source':row['source']['id'],'target':row['target']['id']})
                return {'nodes':list(nodes.values()),'edges':edges,'query_engine':'neo4j'}
            except Exception as exc:
                self.error=f'Neo4j query failed: {type(exc).__name__}. Using local graph.'
        if node not in self.graph:
            return {'nodes':[], 'edges':[]}
        neighbors = list(self.graph.neighbors(node))[:60]
        sub = self.graph.subgraph([node]+neighbors)
        return {'nodes':[{'id':n,**d} for n,d in sub.nodes(data=True)],'edges':[{'source':a,'target':b,**d} for a,b,d in sub.edges(data=True)],'query_engine':'networkx'}

    def recommend(self, source, request, weights):
        indices={p.product_id:i for i,p in enumerate(self.products)}
        results=[]
        remote_ids=None
        if self.backend=='neo4j' and not self.error:
            try:
                remote_ids={row['id'] for row in self.remote_query('MATCH (:SubstiGraph {id: $id})-[:PRODUCT_SUBSTITUTE_FOR]-(p:SubstiGraph) RETURN p.product_id AS id',id=f'product:{source.product_id}')}
            except Exception as exc:
                self.error=f'Neo4j query failed: {type(exc).__name__}. Using local candidates.'
        for p in self.products:
            if remote_ids is not None and p.product_id not in remote_ids:
                continue
            edge=self.graph.get_edge_data(f'product:{source.product_id}',f'product:{p.product_id}')
            if p.product_id==source.product_id or not edge or edge['relation']!='PRODUCT_SUBSTITUTE_FOR' or p.status!='active':
                continue
            deviation=abs(p.price-source.price)/source.price
            if deviation>request.max_price_deviation or (request.require_available and p.stock_quantity<=0):
                continue
            if any(p.specifications.get(k)!=v for k,v in request.required_specs.items()):
                continue
            keys=set(source.attributes)|set(p.attributes)
            matching={k:source.attributes[k] for k in keys if k in source.attributes and source.attributes[k]==p.attributes.get(k)}
            differing={k:{'original':source.attributes.get(k),'substitute':p.attributes.get(k)} for k in keys if k not in matching}
            components={'attribute':100*len(matching)/max(1,len(keys)), 'semantic':float(self.similarities[indices[source.product_id],indices[p.product_id]])*100,'category':100,'price':max(0,100*(1-deviation)),'availability':min(100,p.stock_quantity/20*100),'brand':100 if source.brand==p.brand else 0}
            score=sum(components[k]*weights[k]/100 for k in weights)
            results.append({'product':serialize(p),'score':round(score,2),'components':{k:round(v,2) for k,v in components.items()},'price_difference':round(p.price-source.price,2),'matching_attributes':matching,'differing_attributes':differing,'explanation':f'{p.product_name} matches the {source.subcategory} subcategory and all recorded specifications. {len(matching)} of {len(keys)} attributes match; price difference is {p.price-source.price:+.2f}; {p.stock_quantity} units are in stock. Ranking uses configured business weights.','evidence_ids':[source.product_id,p.product_id]})
        results.sort(key=lambda r:(-r['score'],r['product']['product_id']))
        return {'original':serialize(source),'eligible_count':len(results),'results':results[:request.limit] if request.limit else results,'mode':self.semantic_mode,'explanation_mode':'deterministic','message':None if results else 'No eligible substitute meets the category, specifications, price and inventory constraints.'}

def optimize(products, request):
    import pulp
    eligible=[p for p in products if p.status=='active' and p.stock_quantity>0]
    problem=pulp.LpProblem('assortment',pulp.LpMaximize)
    variables={p.product_id:pulp.LpVariable(f'p{p.product_id}',cat='Binary') for p in eligible}
    # One stocked unit per selected SKU; sales is a historical demand proxy.
    problem += pulp.lpSum(variables[p.product_id]*max(0,p.price-p.cost)*np.log1p(p.sales_quantity) for p in eligible)
    problem += pulp.lpSum(variables[p.product_id]*p.cost for p in eligible)<=request.budget
    problem += pulp.lpSum(variables.values())<=request.max_products
    for category in sorted(set(p.category for p in products)):
        problem += pulp.lpSum(variables[p.product_id] for p in eligible if p.category==category)>=request.min_per_category
    # Limit near-identical variants per subcategory to reduce redundancy.
    for sub in set(p.subcategory for p in eligible):
        problem += pulp.lpSum(variables[p.product_id] for p in eligible if p.subcategory==sub)<=max(1,int(np.ceil(request.max_products/len(set(p.subcategory for p in eligible))))+1)
    problem.solve(pulp.PULP_CBC_CMD(msg=False,timeLimit=20))
    status=pulp.LpStatus[problem.status]
    if status!='Optimal':
        return {'status':status,'products':[],'message':'No proven optimal solution. Relax the budget, SKU cap, or minimum category coverage.'}
    chosen=[p for p in eligible if variables[p.product_id].value()>.5]
    return {'status':status,'products':[serialize(p) for p in chosen],'total_cost':round(sum(p.cost for p in chosen),2),'categories_covered':len(set(p.category for p in chosen)),'objective':round(pulp.value(problem.objective) or 0,2),'assumptions':'Selects one unit per SKU. Historical sales proxy; no causal demand forecast. Subcategory caps reduce redundancy.'}
