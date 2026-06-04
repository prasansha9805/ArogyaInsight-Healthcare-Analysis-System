# analytics.py
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from database import get_connection

BLUE    = "#2563EB"
GREEN   = "#16A34A"
RED     = "#DC2626"
AMBER   = "#D97706"
PURPLE  = "#7C3AED"
GRAY    = "#E5E7EB"
BG      = "#FFFFFF"
TEXT    = "#1a1a1a"


def _no_reaction(val):
    """Return True if this is NOT a reaction (i.e. no adverse effect)."""
    return str(val).strip().lower() in ["no", "none", ""]


def load_all_records() -> pd.DataFrame:
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM patient_records", conn)
    df["Recovery"] = df["Recovery"].str.strip().str.title()
    df["Reaction"] = df["Reaction"].str.strip()
    return df


def search_patient(query: str) -> list[dict]:
    q = query.strip()
    sql = """
        SELECT * FROM patient_records
        WHERE Patient_ID = ?
           OR LOWER(Name) LIKE LOWER(?)
        ORDER BY Visit_Date DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (q, f"%{q}%")).fetchall()
    return [dict(r) for r in rows]


def analyse_medicine(medicine_name: str) -> dict:
    df = load_all_records()
    med_df = df[df["Medicine"].str.lower() == medicine_name.strip().lower()]

    if med_df.empty:
        return {"found": False, "medicine": medicine_name}

    total        = len(med_df)
    recovered    = (med_df["Recovery"] == "Fully Recovered").sum()
    reacted      = (~med_df["Reaction"].apply(_no_reaction)).sum()
    recovery_pct = round((recovered / total) * 100, 1)
    reaction_pct = round((reacted  / total) * 100, 1)

    # Reaction types count karo
    reaction_df     = med_df[~med_df["Reaction"].apply(_no_reaction)]
    reaction_counts = reaction_df["Reaction"].value_counts()

    # ── Chart ─────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(BG)
    fig.suptitle(f"{medicine_name.title()} — Efficacy Report (n={total})",
                 fontsize=12, fontweight="bold", color=TEXT, y=1.01)

    # LEFT — Recovery pie chart
    wedges, _, autotexts = axes[0].pie(
        [recovery_pct, 100 - recovery_pct],
        labels=None,
        colors=[GREEN, GRAY],
        autopct="%1.1f%%", startangle=90,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        textprops={"color": TEXT},
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    axes[0].set_title("Recovery Rate", fontsize=10, fontweight="600", pad=10, color=TEXT)
    axes[0].set_facecolor(BG)
    axes[0].legend(wedges, ["Fully Recovered", "Not Recovered"],
                   loc="lower center", bbox_to_anchor=(0.5, -0.18), fontsize=8, framealpha=0)

    # RIGHT — Reaction types bar chart
    axes[1].set_facecolor(BG)
    if not reaction_counts.empty:
        bars = axes[1].barh(
            reaction_counts.index,
            reaction_counts.values,
            color=RED, edgecolor="white", height=0.5
        )
        for bar, val in zip(bars, reaction_counts.values):
            axes[1].text(
                bar.get_width() + 0.3,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold", color=TEXT
            )
        axes[1].set_xlabel("Count", fontsize=9, color=TEXT)
        axes[1].set_title("Reaction Types", fontsize=10, fontweight="600", pad=10, color=TEXT)
        axes[1].tick_params(colors=TEXT, labelsize=8)
        axes[1].xaxis.grid(True, color=GRAY, linewidth=0.6, linestyle="--")
        axes[1].set_axisbelow(True)
        axes[1].set_xlim(0, reaction_counts.values.max() + 3)
        for spine in axes[1].spines.values():
            spine.set_edgecolor(GRAY)
    else:
        axes[1].text(0.5, 0.5, "No Reactions Found",
                     ha="center", va="center", fontsize=11, color=TEXT)
        axes[1].set_title("Reaction Types", fontsize=10, fontweight="600", pad=10, color=TEXT)
        axes[1].axis("off")

    plt.tight_layout()
    plt.savefig("static/charts/medicine_chart.png", dpi=130,
                bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    return {
        "found":            True,
        "medicine":         medicine_name.title(),
        "total_prescribed": int(total),
        "recovery_rate":    recovery_pct,
        "reaction_rate":    reaction_pct,
    }


def generate_doctor_chart() -> pd.DataFrame:
    df = load_all_records()

    grouped = df.groupby("Doctor").agg(
        Total_Patients  = ("Patient_ID", "count"),
        Fully_Recovered = ("Recovery", lambda s: (s == "Fully Recovered").sum()),
        Avg_Age         = ("Age", "mean"),
    ).reset_index()

    grouped["Recovery_Rate"] = (
        grouped["Fully_Recovered"] / grouped["Total_Patients"] * 100
    ).round(1)

    grouped = grouped.sort_values("Recovery_Rate", ascending=False).reset_index(drop=True)
    grouped["Rank"] = grouped.index + 1

    # ── Chart ────────────────────────────────────────────
    doctors    = grouped["Doctor"].str.replace("Dr. ", "", regex=False)
    rates      = grouped["Recovery_Rate"].values
    totals     = grouped["Total_Patients"].values
    x          = np.arange(len(doctors))
    bar_colors = [GREEN if r >= 70 else AMBER if r >= 50 else RED for r in rates]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    bars = ax.bar(x, rates, color=bar_colors, width=0.5,
                  edgecolor="white", linewidth=1.2)

    for bar, rate, total in zip(bars, rates, totals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{rate}%\n({total} pts)",
            ha="center", va="bottom",
            color=TEXT, fontsize=8.5, fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(doctors, fontsize=9, color=TEXT)
    ax.set_ylabel("Recovery Rate (%)", fontsize=9, color=TEXT)
    ax.set_ylim(0, max(rates) + 18)
    ax.set_title("Doctor Performance — Recovery Rate Ranking",
                 fontsize=11, fontweight="bold", pad=12, color=TEXT)
    ax.tick_params(colors=TEXT)
    ax.yaxis.grid(True, color=GRAY, linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRAY)

    patches = [
        mpatches.Patch(color=GREEN, label="≥ 70% Good"),
        mpatches.Patch(color=AMBER, label="50–69% Average"),
        mpatches.Patch(color=RED,   label="< 50% Low"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=8, framealpha=0)

    plt.tight_layout()
    plt.savefig("static/charts/doctor_chart.png", dpi=130,
                bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    return grouped


def get_summary_kpis() -> dict:
    df = load_all_records()
    if df.empty:
        return {}

    total           = len(df)
    fully_recovered = (df["Recovery"] == "Fully Recovered").sum()
    reaction_count  = (~df["Reaction"].apply(_no_reaction)).sum()
    avg_age         = round(df["Age"].mean(), 1)
    top_disease     = df["Disease"].value_counts().idxmax()
    top_medicine    = df["Medicine"].value_counts().idxmax()

    # Most reactive medicine — jo medicine sabse zyada reactions de rahi hai
    reaction_df     = df[~df["Reaction"].apply(_no_reaction)]
    most_reactive   = reaction_df["Medicine"].value_counts().idxmax() \
                      if not reaction_df.empty else "N/A"

    return {
        "total_patients":       int(total),
        "recovery_rate":        round(fully_recovered / total * 100, 1),
        "reaction_rate":        round(reaction_count  / total * 100, 1),
        "avg_age":              avg_age,
        "top_disease":          top_disease,
        "top_medicine":         top_medicine,
        "most_reactive_medicine": most_reactive,
    }