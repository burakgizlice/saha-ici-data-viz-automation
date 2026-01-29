#!/usr/bin/env python3
"""
Duel Visualization Generator

Automatically fetches duel statistics from Sofascore and generates
a visualization chart showing player duel performance.

Usage:
    python generate_duels_viz.py 14566935
    python generate_duels_viz.py 14566935 --team "Fenerbahçe"
    python generate_duels_viz.py 14566935 --output my_chart.png
"""

import argparse
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ScraperFC as sfc

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "background": "#151410",
    "won": "#65c2a5",
    "lost": "#CC444B",
    "text": "white",
}

LEGEND_TOTAL_WIDTH = 6.0

# Turkish month names for date formatting
TURKISH_MONTHS = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}

# Turkish tournament name translations
TURKISH_TOURNAMENTS = {
    "UEFA Champions League": "Şampiyonlar Ligi",
    "Süper Lig": "Süper Lig",
    "Turkish Cup": "Ziraat Türkiye Kupası",
    "Turkish Super Cup": "Süper Kupa",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────


def fetch_match_info(ss: sfc.Sofascore, match_id: int) -> dict:
    """Fetch match metadata: teams, competition, date, score."""
    match_dict = ss.get_match_dict(match_id)

    date = datetime.fromtimestamp(match_dict["startTimestamp"])
    formatted_date = f"{date.day} {TURKISH_MONTHS[date.month]} {date.year}"

    # Translate tournament name to Turkish if available
    tournament_en = match_dict["tournament"]["name"]
    tournament = TURKISH_TOURNAMENTS.get(tournament_en, tournament_en)

    return {
        "home_team": match_dict["homeTeam"]["name"],
        "away_team": match_dict["awayTeam"]["name"],
        "home_score": match_dict["homeScore"]["current"],
        "away_score": match_dict["awayScore"]["current"],
        "tournament": tournament,
        "season": "2025/2026",
        "date": formatted_date,
    }


def fetch_player_duels(ss: sfc.Sofascore, match_id: int, team_name: str) -> list[dict]:
    """
    Fetch and process player duel data for the specified team.

    Filters: starting XI only, no goalkeeper
    Sorted by: duelTotal DESC, duelWon DESC
    Returns: [{player, minutes, won, lost}, ...]
    """
    players = ss.scrape_player_match_stats(match_id)

    # Remove duplicate columns (e.g., jerseyNumber appears twice)
    players = players.loc[:, ~players.columns.duplicated()]

    # Filter: exclude goalkeeper, only starters, only target team
    players = players[players["position"] != "G"]
    players = players[players["substitute"] == False]  # noqa: E712
    players = players[players["teamName"] == team_name]

    # Handle NaN values
    players = players.fillna(0.0).infer_objects(copy=False)

    # Calculate total duels
    players["duelTotal"] = players["duelWon"] + players["duelLost"]

    # Sort by total duels (desc), then by wins (desc)
    players = players.sort_values(
        by=["duelTotal", "duelWon"], ascending=[False, False]
    )

    # Convert to list of dicts for visualization
    result = []
    for _, row in players.iterrows():
        result.append(
            {
                "player": row["name"],
                "minutes": int(row["minutesPlayed"]),
                "won": int(row["duelWon"]),
                "lost": int(row["duelLost"]),
            }
        )

    # Reverse so highest duel count is at top of chart
    result.reverse()

    return result


def fetch_team_percentages(
    ss: sfc.Sofascore, match_id: int, team_name: str
) -> dict:
    """
    Fetch team-level duel percentages.

    Returns: {
        team_pct, opponent_pct,
        team_name, opponent_name,
        team_won, opponent_won,
        total
    }
    """
    game = ss.scrape_team_match_stats(match_id)
    game = game[game["period"] == "ALL"]
    duel_row = game[game["name"] == "Duels"].iloc[0]
    ground_row = game[game["name"] == "Ground duels"].iloc[0]
    aerial_row = game[game["name"] == "Aerial duels"].iloc[0]

    # Determine if team is home or away
    teams = ss.get_team_names(match_id)
    is_home = teams[0] == team_name
    opponent_name = teams[1] if is_home else teams[0]

    # Get percentage strings (e.g., "51%")
    team_pct_str = duel_row["home"] if is_home else duel_row["away"]
    opponent_pct_str = duel_row["away"] if is_home else duel_row["home"]

    # Parse percentage strings to integers
    team_pct = int(team_pct_str.replace("%", ""))
    opponent_pct = int(opponent_pct_str.replace("%", ""))

    # Calculate total duels WON by summing ground + aerial duels won
    if is_home:
        team_won = int(ground_row["homeValue"]) + int(aerial_row["homeValue"])
        opponent_won = int(ground_row["awayValue"]) + int(aerial_row["awayValue"])
    else:
        team_won = int(ground_row["awayValue"]) + int(aerial_row["awayValue"])
        opponent_won = int(ground_row["homeValue"]) + int(aerial_row["homeValue"])

    return {
        "team_pct": team_pct,
        "opponent_pct": opponent_pct,
        "team_name": team_name,
        "opponent_name": opponent_name,
        "team_won": team_won,
        "opponent_won": opponent_won,
        "total": team_won + opponent_won,
    }


# ─────────────────────────────────────────────────────────────────────────────
# VISUALIZATION
# ─────────────────────────────────────────────────────────────────────────────


def create_chart(
    players: list[dict],
    match_info: dict,
    team_stats: dict,
    output_path: str,
) -> None:
    """Generate the duel visualization chart."""

    fig = plt.figure(figsize=(8, 12))
    fig.patch.set_facecolor(COLORS["background"])

    # ── TITLE SECTION ────────────────────────────────────────────────────────
    title_section = fig.add_axes([0, 0.83, 0.13, 0.06])
    title_section.set_facecolor(COLORS["background"])

    # Main title
    title_section.text(
        0.02,
        0.65,
        s="İkili Mücadeleler",
        ha="left",
        va="center",
        fontsize=20,
        fontweight="bold",
        color=COLORS["text"],
    )

    # Subtitle with match info
    home = match_info["home_team"]
    away = match_info["away_team"]
    home_score = match_info["home_score"]
    away_score = match_info["away_score"]
    tournament = match_info["tournament"]
    print(f"Tournament: {tournament}")
    season = match_info["season"]
    date = match_info["date"]

    subtitle = f"{tournament} - {season} | {home} {home_score} - {away_score} {away} ({date})"

    title_section.text(
        0.02,
        0.28,
        s=subtitle,
        ha="left",
        va="center",
        fontsize=12,
        color=COLORS["text"],
    )

    title_section.set_xlim(0, 1)
    title_section.set_ylim(0, 1)
    title_section.set_xticks([])
    title_section.set_yticks([])
    for spine in title_section.spines.values():
        spine.set_visible(False)

    # ── PREPARE DATA ARRAYS ──────────────────────────────────────────────────
    names = [p["player"] for p in players]
    won_arr = np.array([p["won"] for p in players], dtype=float)
    lost_arr = np.array([p["lost"] for p in players], dtype=float)
    minutes_arr = [p["minutes"] for p in players]
    totals = won_arr + lost_arr
    y_pos = np.arange(len(players))
    bar_height = 0.8

    # ── CHART SECTION ────────────────────────────────────────────────────────
    chart_section = fig.add_axes([0.33, 0.335, 0.66, 0.5])
    chart_section.set_facecolor(COLORS["background"])
    chart_section.set_yticks(y_pos)
    chart_section.set_yticklabels([])
    chart_section.set_ylim(-0.5, len(players) - 0.5)

    # Set x limit so totals/labels fit (minimal padding for longer bars)
    xmax = int(np.max(totals) + 1.5)
    chart_section.set_xlim(0, xmax)

    # Draw stacked horizontal bars
    bar1 = chart_section.barh(
        y_pos,
        won_arr,
        height=bar_height,
        color=COLORS["won"],
        edgecolor=COLORS["won"],
        linewidth=1,
    )
    bar2 = chart_section.barh(
        y_pos,
        lost_arr,
        left=won_arr,
        height=bar_height,
        color=COLORS["lost"],
        edgecolor=COLORS["lost"],
        linewidth=1,
    )

    # Labels inside bars (only if > 0)
    chart_section.bar_label(
        bar1,
        labels=[str(int(v)) if v > 0 else "" for v in won_arr],
        label_type="center",
        color=COLORS["text"],
        weight="bold",
        fontsize=12,
    )
    chart_section.bar_label(
        bar2,
        labels=[str(int(v)) if v > 0 else "" for v in lost_arr],
        label_type="center",
        color=COLORS["text"],
        weight="bold",
        fontsize=12,
    )

    # Total number to the right of each bar
    for i, tot in enumerate(totals):
        chart_section.text(
            tot + 0.25,
            y_pos[i],
            str(int(tot)),
            va="center",
            color=COLORS["text"],
            fontsize=12,
            fontweight="bold",
        )

    for spine in chart_section.spines.values():
        spine.set_visible(False)

    # ── PLAYERS SECTION ──────────────────────────────────────────────────────
    players_section = fig.add_axes([0, 0.335, 0.20, 0.5])
    players_section.set_facecolor(COLORS["background"])
    players_section.set_xlim(0, 1)
    players_section.set_ylim(-0.5, len(players) - 0.5)
    players_section.set_xticks([])
    players_section.set_yticks([])

    for spine in players_section.spines.values():
        spine.set_visible(False)

    # Draw player names and minutes
    for i, p in enumerate(players):
        players_section.text(
            0.02,
            y_pos[i],
            p["player"],
            fontsize=11,
            va="center",
            ha="left",
            color=COLORS["text"],
            weight="bold",
        )
        players_section.text(
            0.02,
            y_pos[i] - 0.30,
            f'{p["minutes"]} dakika',
            fontsize=9,
            va="center",
            ha="left",
            color=COLORS["text"],
            weight="ultralight",
        )

    # ── LEGEND TITLE ─────────────────────────────────────────────────────────
    legend_title = fig.add_axes([0.33, 0.315, 0.74, 0.03])
    legend_title.set_facecolor(COLORS["background"])
    legend_title.text(
        0,
        0.55,
        s="İkili Mücadele Sayıları ve Kazanım Oranları",
        ha="left",
        va="center",
        fontsize=12,
        color=COLORS["text"],
    )
    legend_title.set_xticks([])
    legend_title.set_yticks([])
    for spine in legend_title.spines.values():
        spine.set_visible(False)

    # ── LEGEND SECTION ───────────────────────────────────────────────────────
    legend_section = fig.add_axes([0.33, 0.28, 0.78, 0.040])
    legend_section.set_facecolor(COLORS["background"])
    legend_section.set_xticks([])
    legend_section.set_yticks([])
    for spine in legend_section.spines.values():
        spine.set_visible(False)

    # Calculate bar widths based on percentages
    team_bar_width = (team_stats["team_pct"] / 100) * LEGEND_TOTAL_WIDTH
    opponent_bar_width = LEGEND_TOTAL_WIDTH - team_bar_width

    lbar1 = legend_section.barh(
        1,
        team_bar_width,
        color=COLORS["won"],
        edgecolor=COLORS["won"],
        linewidth=1,
    )
    lbar2 = legend_section.barh(
        1,
        opponent_bar_width,
        left=team_bar_width,
        color=COLORS["lost"],
        edgecolor=COLORS["lost"],
        linewidth=1,
    )

    legend_section.bar_label(
        lbar1,
        labels=[f"%{team_stats['team_pct']} {team_stats['team_name']} - ({team_stats['team_won']})"],
        label_type="center",
        color=COLORS["text"],
        weight="bold",
    )
    legend_section.bar_label(
        lbar2,
        labels=[f"%{team_stats['opponent_pct']} {team_stats['opponent_name']} - ({team_stats['opponent_won']})"],
        label_type="center",
        color=COLORS["text"],
        weight="bold",
    )

    # Total duels at the end
    legend_section.text(
        LEGEND_TOTAL_WIDTH + 0.1,
        1,
        str(team_stats["total"]),
        va="center",
        color=COLORS["text"],
        fontsize=12,
        fontweight="bold",
    )

    # ── SAVE ─────────────────────────────────────────────────────────────────
    fig.savefig(output_path, dpi=600, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Generate duel visualization chart from Sofascore match data"
    )
    parser.add_argument("match_id", type=int, help="Sofascore match ID")
    parser.add_argument(
        "--team",
        default="Galatasaray",
        help="Team to analyze (default: Galatasaray)",
    )
    parser.add_argument(
        "--output",
        default="duels_chart.png",
        help="Output file path (default: duels_chart.png)",
    )
    args = parser.parse_args()

    print(f"Fetching data for match {args.match_id}...")
    ss = sfc.Sofascore()

    match_info = fetch_match_info(ss, args.match_id)
    print(f"Match: {match_info['home_team']} vs {match_info['away_team']}")

    players = fetch_player_duels(ss, args.match_id, args.team)
    print(f"Found {len(players)} starting players for {args.team}")

    team_stats = fetch_team_percentages(ss, args.match_id, args.team)
    print(f"Team duel percentage: {team_stats['team_pct']}%")

    create_chart(players, match_info, team_stats, args.output)
    print(f"Chart saved to {args.output}")


if __name__ == "__main__":
    main()
