"""Plot every registered domain from the complete fixed-interpretation audit."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary',type=Path,required=True)
    p.add_argument('--output-prefix',type=Path,required=True)
    a=p.parse_args();s=json.loads(a.summary.read_bytes())
    assert s['executions']==240 and s['distinct_tasks']==60
    indexed={(r['domain'],r['model'],r['condition']):r for r in s['groups']}
    domains=['computer_student','cars','book_publishing_company']
    names=['Student / courses','Cars','Publishing']
    colors=['#2878A5','#D58939']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.7),sharey=True)
    plotted=[]
    for ax,model,title in zip(axes,['qwen3','qwen25'],['Qwen3-4B-Instruct-2507','Qwen2.5-7B-Instruct']):
        for j,condition in enumerate(['original','coverage_check']):
            for i,domain in enumerate(domains):
                r=indexed[(domain,model,condition)];n=r['clear_interpretation_n'];k=r['correct']
                assert n==[17,18,20][i]
                xpos=i+(j-.5)*.34;value=100*k/n
                ax.bar(xpos,value,width=.31,color=colors[j],zorder=3)
                ax.text(xpos,value+2,f'{k}/{n}',ha='center',va='bottom',fontsize=9)
                plotted.append({'domain':domain,'model':model,'condition':condition,'correct':k,'n':n})
        ax.set_title(title,fontsize=11,pad=12)
        ax.set_xticks(range(3),names);ax.set_ylim(0,100);ax.set_yticks(range(0,101,20))
        ax.grid(axis='y',color='#E5E9EE',zorder=0)
    axes[0].set_ylabel('Correct under fixed SQL interpretation (%)')
    fig.suptitle('A fixed coverage reminder transfers unevenly across domains',fontsize=13,y=.98)
    fig.legend(handles=[Patch(color=colors[0],label='Original prompt'),Patch(color=colors[1],label='Coverage reminder')],
               loc='upper center',bbox_to_anchor=(.5,.90),ncol=2,frameon=False)
    fig.text(.5,.055,'240 executions on 60 shared task identities; descriptive paired comparison.',ha='center',fontsize=9)
    fig.text(.5,.02,'Assistant-authored SQL audit, not official VAKRA scores. Five preidentified ambiguous tasks reported separately.',ha='center',fontsize=8)
    fig.subplots_adjust(top=.76,bottom=.19,wspace=.16,left=.085,right=.985)
    a.output_prefix.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ('.png','.pdf','.svg','.json'):assert not a.output_prefix.with_suffix(suffix).exists()
    for suffix in ('.png','.pdf','.svg'):fig.savefig(a.output_prefix.with_suffix(suffix),dpi=180)
    plt.close(fig)
    a.output_prefix.with_suffix('.json').write_text(json.dumps({'summary_sha256':hashlib.sha256(a.summary.read_bytes()).hexdigest(),
        'rows':plotted,'note':'No inferred error bars; no population significance claim.'},indent=2),encoding='utf-8')
    print('Saved PNG, PDF, SVG and source-data JSON.')


if __name__=='__main__':main()
