"""Render the verified publishing witness and evaluator-authored repair."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def main():
    ev = Path('research/evidence')
    paths = [ev / 'vakra_publishing_contract_audit_v1.json', ev / 'vakra_publishing_contract_repair_v1.json']
    audit, repair = [json.loads(p.read_bytes()) for p in paths]
    row = next(r for r in audit['rows'] if r['source'] == 'original/qwen3/shard-0/case-007.json')
    assert row['baseline_replay']['preserved'] and row['baseline_replay']['calls_checked'] == 3
    assert row['witness']['observation_sha256'] == row['baseline_replay']['observation_sha256']
    counts = [len(row['witness'][k]) for k in ('original_answer', 'counterfactual_answer')]
    assert counts == [17, 16]
    assert [len(r['deduplicated_title_sales_pairs']) for r in repair['results']] == counts
    assert all(r['matches_frozen_sql'] for r in repair['results'])
    assert row['witness']['mutation']['changes'][0] == {'key': ['238-95-7766'], 'before': '0', 'after': '1'}
    fig, ax = plt.subplots(figsize=(10.6, 5.3))
    ax.set(xlim=(0, 10.6), ylim=(0, 5.3)); ax.axis('off')
    plt.rcParams['svg.fonttype'] = 'none'

    def box(x, y, w, h, text, color='#edf2f8', size=10.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.06',
                                   linewidth=0.8, edgecolor='#526176', facecolor=color))
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=size, linespacing=1.4)

    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={'arrowstyle': '->', 'color': '#526176', 'lw': 1.2})

    box(0.15, 4.3, 4.8, 0.8, "Original world\n23 authors: contract = '0'")
    box(5.65, 4.3, 4.8, 0.8, "Counterfactual world\nOne later author's contract: '0' → '1'", '#fff0df')
    ax.text(5.3, 3.95, 'All other database cells fixed; target initialization is identical',
            ha='center', fontsize=10)
    arrow(2.55, 4.22, 2.55, 3.57); arrow(8.05, 4.22, 8.05, 3.57)
    box(0.15, 2.63, 10.3, 0.88,
        "Recorded agent calls in both worlds\nFilter contract ≠ 'Y'; retrieve complete title and sales columns", '#f0f3f5')
    arrow(5.3, 2.57, 5.3, 2.23)
    box(0.15, 1.4, 10.3, 0.77,
        'Identical full tool observations; recorded agent answer: 17 pairs\nRequired answer: 17 pairs in original world; 16 in counterfactual world', '#fff0df')
    box(0.15, 0.3, 10.3, 0.8,
        "Evaluator-authored diagnostic: replace only the filter with contract = '0'\nSame getters now return 17 versus 16 pairs, matching both SQL answers", '#eaf5ec', 10)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.02)
    out = Path('research/paper2/figures'); out.mkdir(exist_ok=True, parents=True)
    for suffix in ('svg', 'png'):
        fig.savefig(out / ('contract_counterexample.' + suffix), dpi=180, facecolor='white')
    svg = out / 'contract_counterexample.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    plt.close(fig)
    source = {'inputs_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'episode': row['source'], 'answer_counts': counts,
              'observation_sha256': row['witness']['observation_sha256'],
              'limits': 'Post-outcome synthetic binary-status intervention; repair is evaluator-authored, not model success.'}
    (out / 'contract_counterexample_source.json').write_text(json.dumps(source, indent=2))
    print(json.dumps(source))


if __name__ == '__main__':
    main()
