import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy import stats

plt.rcParams.update({
    'font.family':'serif','font.serif':['DejaVu Serif'],
    'font.size':10,'axes.titlesize':11,'axes.labelsize':10,
    'figure.dpi':130,'savefig.dpi':200,'axes.grid':True,
    'grid.alpha':0.25,'grid.linewidth':0.5,'axes.axisbelow':True,
})
INK='#1a1a1a'; ACC='#8b1a1a'; GOLD='#b8860b'; STEEL='#2c4a6e'
FIG='output/figures/'

tx = pd.read_csv('output/transactions_all.csv')
s  = tx[tx.unit=='sila3']
b  = s[(s.commodity=='barley') & (s.quantity>0)]

# ---- FIG 1: transaction-size distribution (log) ----
fig, ax = plt.subplots(figsize=(6.5,4))
q = b.quantity.values
lq = np.log10(q)
ax.hist(lq, bins=70, color=STEEL, edgecolor='white', linewidth=0.3, alpha=0.9)
ax.axvline(np.log10(np.median(q)), color=ACC, ls='--', lw=1.4, label=f'median = {np.median(q):.0f} sila₃ (1 gur)')
ax.axvline(np.log10(stats.gmean(q)), color=GOLD, ls=':', lw=1.6, label=f'geom. mean = {stats.gmean(q):.0f} sila₃')
ax.set_xlabel('Transaction size  (log₁₀ sila₃)')
ax.set_ylabel('Number of transactions')
ax.set_title('(a)  Barley transaction-size distribution  (N = 52,678)')
ax.legend(frameon=False, fontsize=8.5)
ax.set_xticks(range(0,8))
ax.set_xticklabels(['1','10','100','1k','10k','100k','1M','10M'])
plt.tight_layout(); plt.savefig(FIG+'fig1_txsize.png'); plt.close()

# ---- FIG 2: Lorenz curve ----
fig, ax = plt.subplots(figsize=(5.2,5))
def lorenz(x):
    x=np.sort(x); c=np.cumsum(x)/x.sum()
    return np.insert(c,0,0)
for data,col,lab in [(b.quantity.values,STEEL,'transactions'),
                      (b.groupby(b.tablet_id).quantity.sum().values,ACC,'tablets')]:
    L=lorenz(data); p=np.linspace(0,1,len(L))
    def g(x):
        x=np.sort(x);n=len(x);i=np.arange(1,n+1)
        return (2*np.sum(i*x)/(n*np.sum(x)))-(n+1)/n
    ax.plot(p,L,color=col,lw=1.8,label=f'{lab}  (G = {g(data):.3f})')
ax.plot([0,1],[0,1],color=INK,ls='--',lw=1,label='equality')
ax.fill_between(p,L,p,color=ACC,alpha=0.06)
ax.set_xlabel('Cumulative share of units (ranked low→high)')
ax.set_ylabel('Cumulative share of barley volume')
ax.set_title('(b)  Concentration of barley volume')
ax.legend(frameon=False,fontsize=8.5,loc='upper left')
ax.set_aspect('equal');ax.set_xlim(0,1);ax.set_ylim(0,1)
plt.tight_layout(); plt.savefig(FIG+'fig2_lorenz.png'); plt.close()

# ---- FIG 3: commodity composition ----
by = s.groupby('commodity').quantity.sum().div(300).sort_values(ascending=True)
by = by[by>1000]
fig, ax = plt.subplots(figsize=(6.5,4))
cols=[GOLD if c in('barley','emmer','wheat','flour') else STEEL for c in by.index]
ax.barh(range(len(by)),by.values,color=cols,edgecolor='white',linewidth=0.4)
ax.set_yticks(range(len(by)));ax.set_yticklabels(by.index)
ax.set_xscale('log')
ax.set_xlabel('Volume  (gur, log scale)')
ax.set_title('(c)  Capacity-measured commodity volume')
for i,v in enumerate(by.values):
    ax.text(v*1.1,i,f'{v:,.0f}',va='center',fontsize=7.5,color=INK)
ax.set_xlim(1000, by.max()*3)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=GOLD,label='cereal grain'),Patch(color=STEEL,label='other (beer, oil, dates…)')],
          frameon=False,fontsize=8.5,loc='lower right')
plt.tight_layout(); plt.savefig(FIG+'fig3_commodity.png'); plt.close()

# ---- FIG 4: temporal (Šulgi years) ----
d = tx[(tx.commodity=='barley')&(tx.date_king=='Šulgi')&tx.date_year_number.notna()]
yc = d.date_year_number.astype(int).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6.5,3.6))
ax.bar(yc.index,yc.values,color=STEEL,edgecolor='white',linewidth=0.4,width=0.8)
ax.set_xlabel('Šulgi regnal year')
ax.set_ylabel('Barley transactions')
ax.set_title('(d)  Dated barley transactions across Šulgi’s reign')
ax.axvspan(44.5,48.5,color=GOLD,alpha=0.12)
ax.annotate('archive\npeak\n(yr 45–48)',xy=(46,800),fontsize=8,ha='center',color=INK)
plt.tight_layout(); plt.savefig(FIG+'fig4_temporal.png'); plt.close()

# ---- FIG 5: per-tablet grain (log hist) ----
pt = b.groupby(b.tablet_id).quantity.sum().div(300)
fig, ax = plt.subplots(figsize=(6.5,4))
ax.hist(np.log10(pt[pt>0]),bins=60,color=STEEL,edgecolor='white',linewidth=0.3,alpha=0.9)
ax.axvline(np.log10(pt.median()),color=ACC,ls='--',lw=1.4,label=f'median = {pt.median():.0f} gur')
for thr,lab in [(10000,'10k gur')]:
    ax.axvline(np.log10(thr),color=GOLD,ls=':',lw=1.4,label=f'{lab} (granary scale)')
ax.set_xlabel('Per-tablet barley total  (log₁₀ gur)')
ax.set_ylabel('Number of tablets')
ax.set_title(f'(e)  Per-tablet barley totals  (N = {len(pt):,} tablets)')
ax.legend(frameon=False,fontsize=8.5)
ax.set_xticks(range(-1,6));ax.set_xticklabels(['0.1','1','10','100','1k','10k','100k'])
plt.tight_layout(); plt.savefig(FIG+'fig5_pertablet.png'); plt.close()

print("Figures written:", FIG)
import os
for f in sorted(os.listdir(FIG)): print(" ",f)
