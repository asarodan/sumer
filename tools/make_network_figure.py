import pandas as pd, numpy as np, networkx as nx
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'savefig.dpi':200})
ACC='#8b1a1a';STEEL='#2c4a6e'
tx=pd.read_csv('output/transactions_all.csv')   # normalized
b=tx[(tx.commodity=='barley')&tx.issuer.notna()&tx.recipient.notna()]
G=nx.DiGraph()
for _,r in b.iterrows():
    w=G[r.issuer][r.recipient]['weight']+1 if G.has_edge(r.issuer,r.recipient) else 1
    G.add_edge(r.issuer,r.recipient,weight=w)
wcc=list(nx.weakly_connected_components(G))
giant=G.subgraph(max(wcc,key=len)).copy()
print(f"nodes {G.number_of_nodes()} edges {G.number_of_edges()} dens {nx.density(G):.5f} wcc {len(wcc)} giant {giant.number_of_nodes()}")
bc=nx.betweenness_centrality(giant,k=500,seed=42)
indeg=dict(giant.in_degree())
print("BROKERS:");
for n,v in sorted(bc.items(),key=lambda x:-x[1])[:6]: print(f"  {n} | {v:.3f}")
print("RECIPIENTS:")
for n,v in sorted(indeg.items(),key=lambda x:-x[1])[:6]: print(f"  {n} | {v}")
# figure
deg=dict(giant.degree(weight='weight'));top=set(sorted(deg,key=deg.get,reverse=True)[:120])
H=giant.subgraph(top).copy();H.remove_nodes_from(list(nx.isolates(H)))
fig,ax=plt.subplots(figsize=(7.5,7.5))
pos=nx.spring_layout(H,k=0.45,seed=7,iterations=120)
sizes=[300+4000*bc.get(n,0) for n in H.nodes()];colors=[bc.get(n,0) for n in H.nodes()]
ew=[0.3+0.6*np.log1p(H[u][v]['weight']) for u,v in H.edges()]
nx.draw_networkx_edges(H,pos,ax=ax,alpha=0.18,width=ew,edge_color=STEEL,arrows=False)
nd=nx.draw_networkx_nodes(H,pos,ax=ax,node_size=sizes,node_color=colors,cmap='YlOrRd',edgecolors=ACC,linewidths=0.5)
lab={n:n for n in sorted(H.nodes(),key=lambda x:bc.get(x,0),reverse=True)[:14]}
nx.draw_networkx_labels(H,pos,labels=lab,ax=ax,font_size=7,font_family='serif')
ax.set_title('(f)  Barley exchange network — giant component\nnode size & colour ∝ betweenness centrality (brokerage)',fontsize=10)
ax.axis('off');plt.colorbar(nd,ax=ax,fraction=0.03,pad=0.01,label='betweenness centrality')
plt.tight_layout();plt.savefig('output/figures/fig6_network.png');plt.close()
print("fig6 regenerated")
