import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx

plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'savefig.dpi':200})
ACC='#8b1a1a'; STEEL='#2c4a6e'; GOLD='#b8860b'

tx = pd.read_csv('output/transactions_all.csv')
b = tx[(tx.commodity=='barley') & tx.issuer.notna() & tx.recipient.notna()]
G = nx.DiGraph()
for _,r in b.iterrows():
    w = G[r.issuer][r.recipient]['weight']+1 if G.has_edge(r.issuer,r.recipient) else 1
    G.add_edge(r.issuer,r.recipient,weight=w)
giant = G.subgraph(max(nx.weakly_connected_components(G),key=len)).copy()

# Keep top-degree nodes for legibility
deg = dict(giant.degree(weight='weight'))
top = set(sorted(deg,key=deg.get,reverse=True)[:120])
H = giant.subgraph(top).copy()
H.remove_nodes_from(list(nx.isolates(H)))

bc = nx.betweenness_centrality(giant,k=400,seed=1)
fig,ax = plt.subplots(figsize=(7.5,7.5))
pos = nx.spring_layout(H,k=0.45,seed=7,iterations=120)
sizes=[300+4000*bc.get(n,0) for n in H.nodes()]
colors=[bc.get(n,0) for n in H.nodes()]
ew=[0.3+0.6*np.log1p(H[u][v]['weight']) for u,v in H.edges()]
nx.draw_networkx_edges(H,pos,ax=ax,alpha=0.18,width=ew,edge_color=STEEL,arrows=False)
nd=nx.draw_networkx_nodes(H,pos,ax=ax,node_size=sizes,node_color=colors,cmap='YlOrRd',
                          edgecolors=ACC,linewidths=0.5)
lab={n:n for n in sorted(H.nodes(),key=lambda x:bc.get(x,0),reverse=True)[:14]}
nx.draw_networkx_labels(H,pos,labels=lab,ax=ax,font_size=7,font_family='serif')
ax.set_title('(f)  Barley exchange network — giant component\n'
             'node size & colour ∝ betweenness centrality (brokerage)',fontsize=10)
ax.axis('off')
plt.colorbar(nd,ax=ax,fraction=0.03,pad=0.01,label='betweenness centrality')
plt.tight_layout(); plt.savefig('output/figures/fig6_network.png'); plt.close()
print("network figure written; giant component", giant.number_of_nodes(),"nodes")
