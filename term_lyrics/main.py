# term-lyrics
# Copyright 2025 DaarcyDev
# Modificaciones: Copyright 2026 DairoDev
#
# Licencia MIT — ver LICENSE en la raíz del proyecto.

import subprocess
import time
import uuid
import threading
import sys
import os
import argparse
import bisect
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from term_lyrics.lyrics import fetch_lyrics, get_synced_lyrics
from term_lyrics.display import (
    get_current_song,
    get_song_duration,
    get_song_position,
    render_text_with_alphabet,
    generate_alphabet_dict,
    install_custom_fonts
)

console = Console()
current_render_id = None


def current_index(times, position):
    return max(0, bisect.bisect_right(times, position) - 1)


def display_lyrics_from_current_position(timed, duration, position, render_id,
                                         alphabet_dict, style, surround_lines=3,
                                         current_line_color="white",
                                         surrounding_lines_color="black",
                                         offset=0.0):
    global current_render_id

    if not timed:
        console.print("[red]❌ Lyrics not found.[/red]")
        return

    times = [t for t, _ in timed]
    texts = [x for _, x in timed]
    total_lines = len(timed)

    with Live(console=console, screen=True, refresh_per_second=4) as live:
        while True:
            if render_id != current_render_id:
                return

            current_pos = get_song_position() + offset
            if current_pos > duration:
                return

            current_line = current_index(times, current_pos)
            window_start = max(0, current_line - surround_lines)
            window_end = min(total_lines, current_line + surround_lines + 1)

            rendered_lines = []
            for idx in range(window_start, window_end):
                line = texts[idx]
                art = render_text_with_alphabet(line, alphabet_dict) if alphabet_dict else line

                if style:
                    st = f"bold {current_line_color}" if idx == current_line else f"dim {surrounding_lines_color}"
                else:
                    st = "bold black" if idx == current_line else "dim white"

                rendered_lines.append(Panel(Text(art, style=st), expand=True, padding=(0, 0)))

            live.update(Group(*rendered_lines))
            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(description="🎵 Term-Lyrics: Synchronized lyrics")
    parser.add_argument("--font", type=str, default="Tubes-Regular", help="Name of the .flf font (without extension) or 'none' for plain text")
    parser.add_argument("--style", type=str, dest="style", help="Optional style for lyrics")
    parser.add_argument("--surround_lines", type=int, default=3, help="Lines before and after the current one (default: 3)")
    parser.add_argument("--current-line-color", type=str, default="white")
    parser.add_argument("--surrounding-lines-color", type=str, default="black")
    parser.add_argument("--offset", type=float, default=0.0,
                        help="Ajuste en segundos: positivo atrasa, negativo adelanta")
    parser.set_defaults(style=True)

    args = parser.parse_args()

    font_name = args.font
    style = args.style
    surround_lines = args.surround_lines
    current_line_color = args.current_line_color
    surrounding_lines_color = args.surrounding_lines_color

    global current_render_id

    if font_name.lower() != "none":
        install_custom_fonts()
        font_path = os.path.join(os.path.dirname(__file__), "fonts", f"{font_name}.flf")
        if not os.path.exists(font_path):
            console.print(f"[red]❌ Font '{font_name}' not found in term_lyrics/fonts/[/red]")
            console.print("[yellow]🔤 You can download .flf fonts from: https://github.com/xero/figlet-fonts[/yellow]")
            console.print("📁 Copy the desired font to: `term_lyrics/fonts/` and use the name without extension in --font")
            sys.exit(1)
        alphabet_dict = generate_alphabet_dict(font_name)
    else:
        alphabet_dict = None

    last_song = None
    lyrics_thread = None

    while True:
        artist, title = get_current_song()
        if not artist or not title:
            console.print("⏸️ No song is playing...")
            time.sleep(1)
            continue

        song_id = f"{artist} - {title}"
        if song_id != last_song:
            console.print(f"\n🎵 {title} — {artist}")

            if lyrics_thread and lyrics_thread.is_alive():
                console.print("🔁 Interrupting previous lyric...")
                current_render_id = None
                lyrics_thread.join(timeout=1)
                time.sleep(0.1)

            duration = get_song_duration() or 180
            timed = get_synced_lyrics(artist, title, "", duration)

            if timed is None:
                console.print("[yellow]⚠️ Sin letra sincronizada, usando modo estimado[/yellow]")
                plain = fetch_lyrics(artist, title)
                lines = [l.strip() for l in (plain or "").split("\n") if l.strip()]
                step = duration / max(len(lines), 1)
                timed = [(i * step, l) for i, l in enumerate(lines)]

            position = get_song_position()

            current_render_id = str(uuid.uuid4())
            lyrics_thread = threading.Thread(
                target=display_lyrics_from_current_position,
                args=(timed, duration, position, current_render_id, alphabet_dict,
                      style, surround_lines, current_line_color,
                      surrounding_lines_color, args.offset),
                daemon=True
            )
            lyrics_thread.start()

            last_song = song_id

        time.sleep(2)


if __name__ == "__main__":
    main()
