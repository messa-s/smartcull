import asyncio, json, os, re, subprocess, sys
from pathlib import Path

import flet as ft

try:
    import flet_video as ftv
    HAS_VIDEO = True
except ImportError:
    HAS_VIDEO = False

ROOT = Path(__file__).parent
BACKEND_DIR = ROOT / "models"
BACKEND = str(BACKEND_DIR / os.environ.get("BACKEND", "backend.py"))
CUT = str(BACKEND_DIR / "cut.py")
CLIPS_DIR = ROOT / "clips"


def fmt(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:05.2f}"


def open_path(path):
    path = str(path)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def main(page: ft.Page):
    page.title = "SmartCull - Video Person Search"
    page.padding = 20

    state = {"video": None, "photos": [], "proc": None, "cancelled": False,
             "data": None, "out_dir": None}
    player = {"video": None}

    # ---------- controls ----------
    video_label = ft.Text("No video selected")
    photo_label = ft.Text("No photos selected")
    query = ft.TextField(label="Text query", value="person wearing black", expand=True)
    threshold = ft.TextField(label="Threshold (blank = default)", width=220)
    status = ft.Text("")
    progress = ft.ProgressBar(visible=False)
    results = ft.ListView(expand=True, spacing=4)
    clips_list = ft.ListView(expand=True, spacing=4)
    exact = ft.Checkbox(label="Exact cuts (slower)", value=False)
    player_box = ft.Container(height=320, content=ft.Text("Cut clips will appear here."))

    # ---------- button state ----------
    def refresh_buttons(running: bool = False):
        has_segments = bool(state["data"] and state["data"]["segments"])
        search_btn.disabled = running
        cut_btn.disabled = running or not has_segments
        cancel_btn.disabled = not running
        progress.visible = running
        page.update()

    # ---------- mode switch ----------
    def on_mode_change(e):
        text_row.visible = mode.value == "text"
        photo_row.visible = mode.value == "face"
        page.update()

    mode = ft.RadioGroup(
        value="text",
        on_change=on_mode_change,
        content=ft.Row([
            ft.Radio(value="text", label="Text query"),
            ft.Radio(value="face", label="Face photo(s)"),
        ]),
    )

    # ---------- pickers ----------
    async def pick_video(e):
        files = await ft.FilePicker().pick_files(
            dialog_title="Choose a video",
            file_type=ft.FilePickerFileType.VIDEO,
        )
        if files:
            state["video"] = files[0].path
            video_label.value = files[0].name
            page.update()

    async def pick_photos(e):
        files = await ft.FilePicker().pick_files(
            dialog_title="Choose photo(s) with a clear face",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=True,
        )
        if files:
            state["photos"] = [f.path for f in files]
            photo_label.value = ", ".join(f.name for f in files)
            page.update()

    # ---------- run a script, streaming its progress ----------
    async def run_script(cmd):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=BACKEND_DIR,
        )
        state["proc"] = proc
        err_lines = []

        async def watch_stderr():
            # progress lines end with \r, other lines with \n
            buf = ""
            while True:
                chunk = await proc.stderr.read(256)
                if not chunk:
                    break
                buf += chunk.decode(errors="replace")
                *done, buf = re.split(r"[\r\n]", buf)
                for line in done:
                    if line.strip():
                        err_lines.append(line.strip())
                        status.value = line.strip()
                page.update()

        stdout_data, _ = await asyncio.gather(proc.stdout.read(), watch_stderr())
        await proc.wait()
        state["proc"] = None
        return proc.returncode, stdout_data, err_lines

    def fail_message(err_lines):
        if state["cancelled"]:
            state["cancelled"] = False
            return "Cancelled."
        return f"Failed: {err_lines[-1] if err_lines else 'unknown error'}"

    # ---------- search ----------
    async def run_search(e):
        if not state["video"]:
            status.value = "Choose a video first."
            page.update()
            return

        cmd = [sys.executable, BACKEND, "--p", state["video"]]
        if mode.value == "text":
            if not query.value.strip():
                status.value = "Enter a text query."
                page.update()
                return
            cmd += ["-q", query.value.strip()]
        else:
            if not state["photos"]:
                status.value = "Choose at least one photo."
                page.update()
                return
            cmd += ["-ph", *state["photos"]]
        if threshold.value.strip():
            cmd += ["--threshold", threshold.value.strip()]

        # reset previous results and clips
        state["data"] = None
        results.controls.clear()
        clips_list.controls.clear()
        player["video"] = None
        player_box.content = ft.Text("Cut clips will appear here.")
        folder_btn.disabled = True
        status.value = "Starting (the first run downloads models)..."
        refresh_buttons(True)

        rc, out, err_lines = await run_script(cmd)

        if rc != 0:
            status.value = fail_message(err_lines)
            refresh_buttons(False)
            return

        data = json.loads(out.decode())
        state["data"] = data
        segments = data["segments"]
        status.value = f"{len(segments)} segment(s) found in {fmt(data['duration'])} of video."
        results.controls = [
            ft.ListTile(
                title=ft.Text(f"{fmt(s['start'])}  →  {fmt(s['end'])}"),
                subtitle=ft.Text(f"score {s['score']}"),
            )
            for s in segments
        ] or [ft.Text("No matches. Try lowering the threshold.")]
        refresh_buttons(False)

    # ---------- cut ----------
    async def run_cut(e):
        data = state["data"]
        if not data or not data["segments"]:
            return

        out_dir = CLIPS_DIR / Path(data["video"]).stem
        out_dir.mkdir(parents=True, exist_ok=True)
        seg_file = out_dir / "segments.json"
        seg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        cmd = [sys.executable, CUT, "--segments", str(seg_file), "-o", str(out_dir)]
        if exact.value:
            cmd.append("--exact")

        status.value = "Cutting clips..."
        refresh_buttons(True)
        rc, out, err_lines = await run_script(cmd)
        refresh_buttons(False)

        if rc != 0:
            status.value = fail_message(err_lines)
            page.update()
            return

        clips = json.loads(out.decode())["clips"]
        state["out_dir"] = out_dir
        folder_btn.disabled = False
        status.value = f"Cut {len(clips)} clip(s) into {out_dir}"
        show_clips(clips)

    def make_play_handler(index, path):
        async def handler(e):
            video = player["video"]
            if video is not None:
                await video.jump_to(index)
                await video.play()
            else:
                open_path(path)
        return handler

    def show_clips(clips):
        if HAS_VIDEO:
            video = ftv.Video(
                playlist=[ftv.VideoMedia(c["path"]) for c in clips],
                autoplay=False,
                aspect_ratio=16 / 9,
                expand=True,
            )
            player["video"] = video
            player_box.content = video
        else:
            player["video"] = None
            player_box.content = ft.Text("Install flet-video to play clips here (pip install flet-video).")

        clips_list.controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PLAY_CIRCLE),
                title=ft.Text(Path(c["path"]).name),
                subtitle=ft.Text(f"{fmt(c['start'])}  →  {fmt(c['end'])}"),
                trailing=ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    tooltip="Open in system player",
                    on_click=lambda e, p=c["path"]: open_path(p),
                ),
                on_click=make_play_handler(i, c["path"]),
            )
            for i, c in enumerate(clips)
        ]
        page.update()

    def open_folder(e):
        if state["out_dir"]:
            open_path(state["out_dir"])

    def cancel(e):
        if state["proc"]:
            state["cancelled"] = True
            state["proc"].terminate()

    # ---------- buttons and layout ----------
    search_btn = ft.Button("Search", on_click=run_search)
    cancel_btn = ft.OutlinedButton("Cancel", on_click=cancel, disabled=True)
    cut_btn = ft.Button("Cut clips", on_click=run_cut, disabled=True)
    folder_btn = ft.OutlinedButton("Open clips folder", on_click=open_folder, disabled=True)

    text_row = ft.Row([query])
    photo_row = ft.Row([ft.Button("Choose photo(s)", on_click=pick_photos), photo_label], visible=False)

    page.add(
        ft.Row([ft.Button("Choose video", on_click=pick_video), video_label]),
        mode,
        text_row,
        photo_row,
        ft.Row([threshold, search_btn, cancel_btn]),
        progress,
        status,
        ft.Divider(),
        ft.Row(
            expand=True,
            controls=[
                ft.Column(expand=1, controls=[
                    ft.Text("Matches", weight=ft.FontWeight.BOLD),
                    ft.Row([cut_btn, exact], wrap=True),
                    results,
                ]),
                ft.Column(expand=1, controls=[
                    ft.Text("Clips", weight=ft.FontWeight.BOLD),
                    player_box,
                    folder_btn,
                    clips_list,
                ]),
            ],
        ),
    )


ft.run(main)
