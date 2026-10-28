"""Figures for docs/proposals/two_directions.tex.

Direction B numbers are read from results/ in this repository. Direction A numbers come from
pilot 1 (oosterbaanvu/masterthesis_pilot_final, reports/sota_followup/07_incremental_value_and_shared_review_budget.md):
full context, ECAR 5%, mean of five seeds, 40 changed values per case, extra beyond rules, statistics and Ridge.
Run: data/env/bin/python docs/proposals/figures/make_figures.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
TEXT_W = 6.3

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "pdf.fonttype": 42,
})


def hbar(ax, labels, values, color=BLUE, fmt="{:g}", xmax=None, invert=True):
    y = range(len(labels))
    ax.barh(list(y), values, height=0.62, color=color, edgecolor="white", linewidth=1)
    ax.set_yticks(list(y), labels)
    if invert:
        ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    if xmax:
        ax.set_xlim(0, xmax)
    for yi, v in zip(y, values):
        ax.text(v, yi, " " + fmt.format(v), va="center", ha="left", color=INK2, fontsize=7.5)


def fig_a_increment():
    labels = ["Bank: job replaced by\nanother valid job",
              "Credit: education replaced\nby another valid code",
              "Wine: alcohol copied\nfrom a similar record"]
    hits, alerts = [20.6, 11.4, 12.8], [522, 682.6, 903.6]
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXT_W, 1.75), sharey=True)
    hbar(a, labels, hits, xmax=48)
    a.set_title("Extra changed values flagged (of 40)", loc="left")
    hbar(b, labels, alerts, color=ORANGE, fmt="{:.0f}", xmax=1150, invert=False)
    b.set_title("Extra alerts for the reviewer", loc="left")
    fig.tight_layout(w_pad=2)
    fig.savefig(OUT / "fig_a_increment.pdf", bbox_inches="tight")


def fig_b_e1_e5():
    strat = pd.read_csv(ROOT / "results/p3_rules/translate_by_stratum.csv")
    stab = pd.read_csv(ROOT / "results/p3_rules/translate_stability.csv")
    models = [("qwen2.5-coder-7b", "Qwen2.5-Coder-7B", BLUE), ("qwen3-8b", "Qwen3-8B", ORANGE)]
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXT_W, 2.6), gridspec_kw={"width_ratios": [1, 1.35]})

    groups = [("released_before_models", "Released before\nthe models\n(10 rules)"),
              ("released_after_models", "Released after\nthe models\n(6 rules)")]
    w = 0.36
    for i, (m, name, c) in enumerate(models):
        vals = [strat.query("model == @m and stratum == @g").micro_recall.iloc[0] for g, _ in groups]
        xs = [j + (i - 0.5) * w for j in range(len(groups))]
        a.bar(xs, vals, width=w, color=c, edgecolor="white", linewidth=1, label=name)
        for x, v in zip(xs, vals):
            a.text(x, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5, color=INK2)
    a.set_xticks(range(len(groups)), [g[1] for g in groups])
    a.set_ylim(0, 0.6)
    a.set_ylabel("Share of official messages found")
    a.grid(axis="x", visible=False)
    a.set_title("(a) Reproducing official rules", loc="left")
    a.legend(frameon=False, loc="upper right")

    rules = sorted(stab.rule.unique())
    for i, (m, name, c) in enumerate(models):
        sub = stab[stab.model == m].set_index("rule")
        for j, r in enumerate(rules):
            y = j + (i - 0.5) * 0.34
            lo, hi = sub.loc[r, "min"], sub.loc[r, "max"]
            b.plot([lo, hi], [y, y], color=c, linewidth=2, solid_capstyle="round")
            b.scatter([lo, hi], [y, y], s=16, color=c, edgecolor="white", linewidth=0.8, zorder=3,
                      label=name if j == 0 else None)
    b.set_yticks(range(len(rules)), [r.replace("_", " ") for r in rules])
    b.invert_yaxis()
    b.set_xlim(-0.04, 1.04)
    b.set_xlabel("Share of official messages found (lowest and highest of three runs)")
    b.grid(axis="y", visible=False)
    b.tick_params(axis="y", length=0)
    b.set_title("(b) Same rule, written three times", loc="left")
    b.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.02), ncol=2, borderaxespad=0)
    b.set_title("(b) Same rule, written three times", loc="left", pad=16)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(OUT / "fig_b_e1_e5.pdf", bbox_inches="tight")


def fig_b_catch():
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from dqstress.splits import split_of
    stress = ROOT / "results/p2_stress"
    inj = pd.concat([pd.read_csv(p, low_memory=False) for p in sorted(stress.glob("injected_detection*.csv.gz"))],
                    ignore_index=True)
    inj = inj[(inj["applicable"] == True) & (inj["placement"] == "calibrated")]  # noqa: E712
    inj = inj[inj["adsh"].map(split_of) == "test"]
    inj = inj[inj["adsh"].isin(set(inj.loc[inj["control"] == "official_dqc", "adsh"]))]
    stats = ["stat_sign_rarity", "stat_magnitude", "stat_period_jump"]

    def rate(controls):
        part = inj[inj["control"].isin(controls)]
        return part.groupby(["adsh", "operator"])["detected_strict"].any().groupby("operator").mean()

    order = ["sign_flip", "scale_x1000", "changed_amount", "one_digit", "retag", "period_swap", "drop_fact"]
    names = ["Sign flipped", "Value x1000", "Amount changed", "One digit changed",
             "Wrong element", "Periods swapped", "Fact removed"]
    panels = [(rate(stats), "Statistical checks\n(three combined)"),
              (rate(["official_dqc"]), "Official DQC\nrules"),
              (rate(stats + ["generic_schema", "official_dqc"]), "All existing\ncontrols together"),
              (rate(["naive_non_negative"]), "Naive rule:\nnever negative"),
              (rate(["ai_qwen3-8b_gapclose_sample1"]), "Best AI rule set\n(Qwen3-8B)")]
    fig, axes = plt.subplots(1, 5, figsize=(TEXT_W, 2.1), sharey=True)
    for k, (ax, (series, title)) in enumerate(zip(axes, panels)):
        vals = [float(series.get(o, 0.0)) for o in order]
        hbar(ax, names, vals, color=ORANGE if k == 4 else BLUE, fmt="{:.2f}", xmax=1.0, invert=(k == 0))
        for t in ax.texts:
            if t.get_text().strip() == "0.00":
                t.set_text(" 0")
        ax.set_xticks([0, 0.5, 1.0], ["0", "0.5", "1"])
        ax.set_title(title, loc="left", fontsize=7.5)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(OUT / "fig_b_catch.pdf", bbox_inches="tight")


def fig_b_alerts():
    e5 = pd.read_csv(ROOT / "results/summary/E5_alerts_clean_filings.csv").set_index("control")
    e4 = pd.read_csv(ROOT / "results/summary/E4_added_value_dqc_filings.csv").set_index("control")
    rows = [
        ("official_dqc", "Official DQC rules", BLUE, None),
        ("stat_sign_rarity", "Statistics: rare sign", BLUE, None),
        ("stat_magnitude", "Statistics: magnitude", BLUE, None),
        ("stat_period_jump", "Statistics: period jump", BLUE, None),
        ("generic_schema", "Generic checks", BLUE, None),
        ("naive_non_negative", "Naive rule: never negative", BLUE, None),
        ("ai_judge_qwen3 (cap 10)", "AI judge, Qwen3-8B (max. 10)", ORANGE, "ai_judge_qwen3"),
        ("ai_qwen2.5-coder-7b_discover_greedy_repair1", "AI rules, Qwen2.5 discover, repaired", ORANGE,
         "ai_qwen2.5-coder-7b_discover_greedy_repair1"),
        ("ai_qwen3-8b_gapclose_sample1", "AI rules, Qwen3 gap-closing", ORANGE, "ai_qwen3-8b_gapclose_sample1"),
        ("ai_qwen3-8b_discover_sample1", "AI rules, Qwen3 discover", ORANGE, "ai_qwen3-8b_discover_sample1"),
    ]
    fig, ax = plt.subplots(figsize=(TEXT_W, 2.7))
    for i, (key, name, c, e4key) in enumerate(rows):
        v = e5.loc[key, "mean_alerts"]
        ax.barh(i, v - 0.05, height=0.62, color=c, edgecolor="white", linewidth=1, left=0.05,
                label={BLUE: "Existing or simple controls", ORANGE: "AI rules or AI judge"}[c]
                if (i == 0 or (c == ORANGE and rows[i - 1][2] == BLUE)) else None)
        note = f"{v:g}" if v < 100 else f"{v:,.0f}"
        if e4key:
            n = int(e4.loc[e4key, "added_beyond_existing"])
            note += f"   ({n} extra error{'s' if n != 1 else ''} caught)"
        ax.text(v * 1.15, i, note, va="center", ha="left", fontsize=7.5, color=INK2)
    ax.set_xscale("log")
    ax.set_xlim(0.05, 2e5)
    ax.set_yticks(range(len(rows)), [r[1] for r in rows])
    ax.set_ylim(len(rows) - 0.5, -1.3)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.axvline(1, color=INK2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.text(1.1, -0.95, "approval limit: at most 1 alert", fontsize=7, color=INK2, va="center")
    ax.set_xticks([0.1, 1, 10, 100, 1000, 10000], ["0.1", "1", "10", "100", "1,000", "10,000"])
    ax.set_xlabel("Mean alerts on a filing that was never corrected (log scale)")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_b_alerts.pdf", bbox_inches="tight")


def fig_c_qualification():
    curve = pd.read_csv(ROOT / "results/minipilot/qualification_curve.csv")
    base = pd.read_csv(ROOT / "results/minipilot/qualification_results.csv")
    unf = base[base["policy"] == "unfiltered"].iloc[0]
    fig, ax = plt.subplots(figsize=(TEXT_W, 2.6))
    for policy, name, c, m in [("generic_filter", "Generic filter (ignores existing controls)", BLUE, "o"),
                               ("expert_aware", "Expert-aware qualification", ORANGE, "s")]:
        part = curve[curve["policy"] == policy].drop_duplicates(["alerts_per_clean_filing", "added_beyond_existing"])
        part = part[part["alerts_per_clean_filing"] > 0].sort_values("alerts_per_clean_filing")
        ax.plot(part["alerts_per_clean_filing"], part["added_beyond_existing"], color=c, linewidth=2, marker=m,
                markersize=6, markeredgecolor="white", label=name)
    ax.scatter([unf["alerts_per_clean_filing"]], [unf["added_beyond_existing"]], s=40, color=INK2, zorder=3,
               label="All 24 sub-rules, unfiltered")
    ax.axvline(1, color=INK2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.text(1.08, 44, "pilot gate: 1 alert", fontsize=7, color=INK2, va="top")
    ax.set_xscale("log")
    ax.set_xlim(0.1, 3000)
    ax.set_ylim(0, 48)
    ax.set_xticks([0.1, 1, 10, 100, 1000], ["0.1", "1", "10", "100", "1,000"])
    ax.set_xlabel("Mean alerts on a filing that was never corrected (log scale)")
    ax.set_ylabel("Extra errors caught\n(of 195 missed)")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_c_qualification.pdf", bbox_inches="tight")


if __name__ == "__main__":
    fig_a_increment()
    fig_b_e1_e5()
    fig_b_catch()
    fig_b_alerts()
    fig_c_qualification()
