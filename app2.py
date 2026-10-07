import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
import json
from matplotlib.patches import Polygon
import matplotlib as mpl


mpl.rcParams['animation.ffmpeg_path'] = '/opt/homebrew/bin/ffmpeg'

st.set_page_config(page_title="PSV Analytics - SciSports 2D Visualizer", layout="centered")
st.title("PSV 2D Map - SciSports Match Visualizer")
st.write("Upload het **PlayerMatchStats CSV-bestand** én het **SciSportsPositions JSON-bestand** om de MP4-video te genereren.")

# 1. Twee uploadknoppen
col1, col2 = st.columns(2)

with col1:
    csv_file = st.file_uploader("1. PlayerMatchStats (CSV)", type=["csv"])

with col2:
    json_file = st.file_uploader("2. SciSportsPositions (JSON)", type=["json"])

TARGET_TEAM = "PSV W"

def classify_line(pos):
    if pd.isna(pos):
        return None
    p = str(pos).lower()
    if "goalkeeper" in p:
        return "gk"
    if any(k in p for k in ["forward", "wing"]):
        return "attack"
    if any(k in p for k in ["midfield"]):
        return "mid"
    if any(k in p for k in ["back", "defender"]):
        return "def"
    return None

def draw_pitch(ax):
    ax.plot([-52.5, 52.5], [-34, -34], color="white")
    ax.plot([-52.5, 52.5], [34, 34], color="white")
    ax.plot([-52.5, -52.5], [-34, 34], color="white")
    ax.plot([52.5, 52.5], [-34, 34], color="white")
    ax.plot([0, 0], [-34, 34], color="white")
    ax.add_patch(plt.Circle((0, 0), 9.15, color="white", fill=False))
    ax.plot([-52.5, -36], [-20.16, -20.16], color="white")
    ax.plot([-52.5, -36], [20.16, 20.16], color="white")
    ax.plot([-36, -36], [-20.16, 20.16], color="white")
    ax.plot([52.5, 36], [-20.16, -20.16], color="white")
    ax.plot([52.5, 36], [20.16, 20.16], color="white")
    ax.plot([36, 36], [-20.16, 20.16], color="white")
    ax.plot([-52.5, -47], [-9.16, -9.16], color="white")
    ax.plot([-52.5, -47], [9.16, 9.16], color="white")
    ax.plot([-47, -47], [-9.16, 9.16], color="white")
    ax.plot([52.5, 47], [-9.16, -9.16], color="white")
    ax.plot([52.5, 47], [9.16, 9.16], color="white")
    ax.plot([47, 47], [-9.16, 9.16], color="white")
    ax.plot([-52.5, -54.5], [-3.66, -3.66], color="white")
    ax.plot([-52.5, -54.5], [3.66, 3.66], color="white")
    ax.plot([-54.5, -54.5], [-3.66, 3.66], color="white")
    ax.plot([52.5, 54.5], [-3.66, -3.66], color="white")
    ax.plot([52.5, 54.5], [3.66, 3.66], color="white")
    ax.plot([54.5, 54.5], [-3.66, 3.66], color="white")
    LEFT_16 = -36
    RIGHT_16 = 36
    ax.plot([LEFT_16, RIGHT_16], [-20.4, -20.4], color="white", linestyle="--", linewidth=1.5, alpha=0.3)
    ax.plot([LEFT_16, RIGHT_16], [-6.8, -6.8],   color="white", linestyle="--", linewidth=1.5, alpha=0.3)
    ax.plot([LEFT_16, RIGHT_16], [6.8, 6.8],     color="white", linestyle="--", linewidth=1.5, alpha=0.3)
    ax.plot([LEFT_16, RIGHT_16], [20.4, 20.4],   color="white", linestyle="--", linewidth=1.5, alpha=0.3)

def draw_line_group(ax, group_df, color):
    if len(group_df) < 2:
        return

    pts = group_df[["X", "Y"]].sort_values(by="Y").values
    ax.plot(pts[:, 0], pts[:, 1], color=color, linestyle="-", linewidth=2.5, alpha=0.85, zorder=4)

    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i + 1]
        dist = np.hypot(p1[0] - p2[0], p1[1] - p2[1])
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2
        ax.text(mid_x, mid_y, f"{dist:.1f}m", color="black", fontsize=6, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.8, edgecolor=color),
                ha="center", va="center", zorder=6)

# Pas verwerken als BEIDE bestanden zijn geüpload
if csv_file is not None and json_file is not None:
    player_stats = pd.read_csv(csv_file)
    player_stats = player_stats[player_stats["team"].astype(str).str.contains(TARGET_TEAM, case=False, na=False)].copy()

    id_to_name = {}
    player_line_map = {}

    for _, row in player_stats.iterrows():
        pid = str(row["player_id"]).strip()
        full_name = str(row["player"]).strip() if pd.notna(row["player"]) else ""
        last_name = full_name.split()[-1] if full_name else f"Player_{pid}"
        
        id_to_name[pid] = last_name
        player_line_map[pid] = classify_line(row["position"])

    def safe_name(pid):
        pid_str = str(pid).strip()
        return id_to_name.get(pid_str, None)

    data = json.load(json_file)["data"]

    rows = []
    for frame in data:
        t = frame["t"]
        ball = frame.get("b", {})
        ball_x = ball.get("x", np.nan)
        ball_y = ball.get("y", np.nan)
        
        all_players = frame.get("h", []) + frame.get("a", [])
        
        for pl in all_players:
            pid = str(pl["p"]).strip()
            name = safe_name(pid)
            if name is not None:
                rows.append({
                    "Timestamp": t,
                    "playerId": pid,
                    "Name": name,
                    "ShirtNumber": pl["s"],
                    "X": pl["x"],
                    "Y": pl["y"],
                    "BallX": ball_x,
                    "BallY": ball_y,
                    "line_group": player_line_map.get(pid, None)
                })

    df = pd.DataFrame(rows)

    df = df.sort_values(by=["playerId", "Timestamp"]).reset_index(drop=True)

    df["dx"] = df.groupby("playerId")["X"].diff()
    df["dy"] = df.groupby("playerId")["Y"].diff()
    df["dist"] = np.sqrt(df["dx"]**2 + df["dy"]**2)
    df["dt"] = df.groupby("playerId")["Timestamp"].diff() / 1000.0
    df["speed_kmh"] = (df["dist"] / df["dt"]) * 3.6
    df.loc[df["speed_kmh"] > 40, "speed_kmh"] = np.nan
    df["speed_kmh"] = df.groupby("playerId")["speed_kmh"].transform(lambda x: x.rolling(window=5, min_periods=1, center=True).mean())
    frames = np.sort(df["Timestamp"].unique())
    total_frames = len(frames)

    data_by_ts = dict(list(df.groupby("Timestamp")))
    raw_data_by_ts = {f["t"]: f for f in data}

    st.success(f"Beide bestanden succesvol ingeladen! Totaal aantal frames: **{total_frames}**")

    if st.button("▶️ Genereer Video"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("#33AA33")

        def update(frame_idx):
            ts = frames[frame_idx]
            
            frame_data = data_by_ts.get(ts, pd.DataFrame())
            if frame_data.empty:
                return

            raw_frame = raw_data_by_ts.get(ts, {})
            all_raw_players = raw_frame.get("h", []) + raw_frame.get("a", [])
            opponent_rows = [{"X": pl["x"], "Y": pl["y"], "ShirtNumber": pl["s"]} 
                             for pl in all_raw_players if str(pl["p"]).strip() not in id_to_name]
            opponent_df = pd.DataFrame(opponent_rows)

            ax.clear()
            ax.set_facecolor("#33AA33")
            ax.set_xlim(-52.5, 52.5)
            ax.set_ylim(-34, 34)
            ax.set_aspect("equal")
            ax.axis("off")
            fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

            draw_pitch(ax)

            trail_length = 10
            start_idx = max(0, frame_idx - trail_length + 1)
            past_ts = frames[start_idx : frame_idx + 1]

            ball_trail_pts = []
            for t_past in past_ts:
                f_data = data_by_ts.get(t_past, pd.DataFrame())
                if not f_data.empty:
                    bx = f_data["BallX"].iloc[0]
                    by = f_data["BallY"].iloc[0]
                    if not np.isnan(bx) and not np.isnan(by):
                        ball_trail_pts.append((bx, by))

            num_pts = len(ball_trail_pts)
            for i, (bx, by) in enumerate(ball_trail_pts):
                alpha = 0.15 + 0.75 * (i / max(1, num_pts - 1))
                size = 25 + 55 * (i / max(1, num_pts - 1))
                edgecol = "black" if i == num_pts - 1 else "none"
                z_index = 7 if i == num_pts - 1 else 6
                ax.scatter(bx, by, c="white", edgecolors=edgecol, s=size, alpha=alpha, zorder=z_index)

            ax.scatter(frame_data["X"], frame_data["Y"], c="red", s=60, zorder=5)
            
            if not opponent_df.empty:
                ax.scatter(opponent_df["X"], opponent_df["Y"], c="black", s=90, zorder=5)
                for _, row in opponent_df.iterrows():
                    shirt_num = row['ShirtNumber']
                    shirt_str = str(int(shirt_num)) if pd.notna(shirt_num) else ""
                    ax.text(row["X"], row["Y"], shirt_str, fontsize=6, color="white",
                            ha="center", va="center", fontweight="bold", zorder=6)

            minutes = int((ts / 1000) // 60)
            seconds = int((ts / 1000) % 60)
            ax.text(-50, 31, f"Tijd: {minutes:02d}:{seconds:02d}", fontsize=11, fontweight="bold", color="white",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="black", alpha=0.75, edgecolor="none"))

            keeper_ids = frame_data[frame_data["ShirtNumber"].isin([1, 16])]["playerId"].unique()
            field_players = frame_data[~frame_data["playerId"].isin(keeper_ids)]

            if not field_players.empty:
                minX, maxX = field_players["X"].min(), field_players["X"].max()
                minY, maxY = field_players["Y"].min(), field_players["Y"].max()
                
                rect_points = [(minX, minY), (minX, maxY), (maxX, maxY), (maxX, minY)]
                poly = Polygon(rect_points, closed=True, facecolor=(0, 0.45, 1, 0.15), edgecolor=(0, 0.45, 1, 0.4), linewidth=1.5)
                ax.add_patch(poly)

                for i in range(4):
                    a = rect_points[i]
                    b = rect_points[(i + 1) % 4]
                    edge_dist = np.hypot(a[0] - b[0], a[1] - b[1])
                    ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, f"{edge_dist:.1f} m", 
                            color="black", fontsize=6.5, fontweight="bold",
                            ha="center", va="center", zorder=6)

            lines_config = [
                ("def", "#FFFF005A"),
                ("mid", "#00FFFF6B"),
                ("attack", "#FF8C0071")
            ]

            for line_name, color in lines_config:
                group_df = field_players[field_players["line_group"] == line_name]
                draw_line_group(ax, group_df, color)

            for _, row in frame_data.iterrows():
                speed_val = row['speed_kmh'] if not pd.isna(row['speed_kmh']) else 0.0
                shirt_num_psv = int(row['ShirtNumber']) if pd.notna(row['ShirtNumber']) else ""
                ax.text(row["X"] + 0.5, row["Y"] + 0.5, f"{row['Name']} #{shirt_num_psv}\n{speed_val:.1f} km/h", 
                        fontsize=8, color="white",
                        bbox=dict(boxstyle="round,pad=0.15", facecolor="black", alpha=0.5, edgecolor="none"))
                
                dx, dy = row["dx"], row["dy"]
                if not (pd.isna(dx) or pd.isna(dy)):
                    speed = np.hypot(dx, dy)
                    if speed > 0.1:  
                        ax.arrow(row["X"], row["Y"], dx * 2, dy * 2, head_width=0.5, head_length=0.8, fc="red", ec="red")

            progress = (frame_idx + 1) / total_frames
            progress_bar.progress(progress)
            status_text.text(f"Bezig met renderen van frame {frame_idx + 1} van {total_frames} ({int(progress * 100)}%)...")

        ani = FuncAnimation(fig, update, frames=total_frames, interval=100)
        
        output_filename = "SciSports_Match.mp4"
        writer = FFMpegWriter(fps=10, metadata=dict(artist='PSV Analytics'), bitrate=1800)
        ani.save(output_filename, writer=writer)
        plt.close(fig)

        status_text.text("Renderen voltooid!")
        st.success("Klaar! Bekijk en download de video hieronder.")
        
        with open(output_filename, "rb") as video_file:
            video_bytes = video_file.read()
            st.video(video_bytes)
            st.download_button(
                label="Download MP4 Video",
                data=video_bytes,
                file_name="SciSports_Match.mp4",
                mime="video/mp4"
            )
