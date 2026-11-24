# Cartoon AI - video to cartoon converter for Windows

Desktop app (Python + PySide6 + FFmpeg + SQLite). **One file: `Cartoon.exe`**, no Python or other install needed on the PC that runs it.

> ## Honest status
> * The source code is complete and was tested on **Linux** (headless): 17 automatic checks pass (all 7 screens in dark and light mode, FFmpeg editing/export, 10-second limit, database, and the full AI-provider flow against a *mock* server).
> * The same recipe (`cartoon.spec`) was also built into a **single-file Linux program** with FFmpeg bundled inside, and the same 17 checks pass when run from that frozen file. That proves the packaging recipe, but it is **not** a Windows test.
> * **`Cartoon.exe` itself was NOT built or run on Windows by me.** The build machine was Linux and PyInstaller cannot build Windows programs from Linux. The included GitHub workflow builds it on a real Windows machine and runs the same self-test on the finished EXE.
> * Video playback (the preview player) could not be exercised headless here; it is tested only by the workflow's "launch with a real window" step on Windows.
> * The real AI call to Replicate was **not tested against a live account** (no key, no internet access to it here). The default input names for `luma/modify-video` are unverified, so the model + JSON template are editable in Settings.

## How to get Cartoon.exe (no commands on your PC besides git)

1. Extract this zip, create a **new GitHub repository** (private is fine).
2. In Command Prompt inside the extracted `CartoonAI` folder:
   ```
   git init
   git add .
   git commit -m "Cartoon AI"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/cartoon-ai.git
   git push -u origin main
   ```
3. On GitHub open **Actions** -> *Build Cartoon.exe*. It takes about 10-15 minutes.
   * The steps *Self-test from source* and *Self-test the built Cartoon.exe* must be green. They print a PASS/FAIL list.
   * The step *Launch Cartoon.exe with a real window* is allowed to fail without stopping the build; if it is red, tell me.
4. Open **Releases** (right side of the repo page) -> latest *Cartoon.exe build N* -> download **Cartoon.exe** (a plain .exe, not a zip). Also available as the `Cartoon-exe` artifact on the run page (GitHub wraps artifacts in a zip).
5. Double-click `Cartoon.exe`. Windows SmartScreen may say "unknown publisher" because the file is not code-signed: *More info -> Run anyway*.

If the Releases step fails with a permissions error: repo *Settings -> Actions -> General -> Workflow permissions -> Read and write permissions*, then re-run.

Alternative on a Windows PC with Python 3.12: double-click `build_exe.bat` -> `dist\Cartoon.exe`.

## Using the app

* **Demo Mode (no key):** the app applies a plain local colour filter and stamps it *"DEMO - local filter, NOT AI"*. It is never presented as AI output.
* **Real AI (Replicate, cloud, needs internet and pays per use):**
  1. Create an account at replicate.com and add billing.
  2. Copy an API token from replicate.com/account/api-tokens.
  3. In the app: **Settings -> AI service -> paste token -> Save key -> Test connection.**
  The key is stored in Windows Credential Manager, not in a file and not in the code.
  4. Open the model's **API** tab on replicate.com and make sure the *Input template* in Settings uses the same field names. Default: `{"video": "{video}", "prompt": "{prompt}", "mode": "{mode}"}` for `luma/modify-video`.
* The AI accepts **10 seconds maximum**. Longer videos open a trim window automatically; Generate stays disabled until the clip is 10 s or less. Files over 100 MB are refused.

## What is in it

| Area | Included |
|---|---|
| Dashboard | Header (logo, profile, settings), hero banner, quick actions, 6 popular styles, recent projects with status/preview/edit |
| Navigation | Sidebar: Home, AI Video Studio, Animation Styles, Video Editor, My Creations, Settings, About |
| Input | Upload, drag-and-drop, webcam recording (if a camera exists), preview, duration/resolution/fps detection, trim, remove/replace |
| Styles | 15 styles with generated preview art, description and select button |
| AI Studio | Original preview, style, prompt, Style Intensity, auto-enhance, Generate, real status text, cancel, retry, result preview, regenerate, compare, favorite, export |
| Editor (FFmpeg) | Trim, split, crop (ratios/custom), rotate, flip, speed/slow motion, brightness/contrast/saturation, text overlays, subtitles from .srt, volume, remove audio, add music / sound effect / voice-over file, record voice-over |
| Export | MP4, 480p / 720p / 1080p, original / 16:9 / 9:16 / 1:1 (done locally, black bars, nothing cropped) |
| My Creations | Library with search, filter (favorites / generated / originals), rename, delete, preview, export, open in editor |
| Themes | Dark and light mode (Settings) |
| Safety | Invalid/empty/unsupported file detection, size and duration validation, network + API error messages, automatic retries on network/busy errors, temp-file cleanup, key in Credential Manager |

## Limits you should know

* **Only controls the connected model really supports are shown.** With the default model that is: custom prompt, Style Intensity (it chooses how far the model may change the video) and auto-enhance (adds quality words to the prompt). Face consistency, character/motion preservation, background, lighting, colour palette, detail, temporal smoothing and negative prompt are **not offered** by it, so the Studio lists them as unavailable instead of showing fake sliders. A future provider can enable them by listing them in its `capabilities`.
* The AI service decides the size and quality of the generated clip; export resolution/aspect only re-scales it locally.
* Automatic subtitle generation (speech-to-text) is not included. Load an existing .srt or use text overlays.
* Cloud AI cannot work offline.
* Video preview uses Windows' built-in codecs; if a file cannot be previewed it can usually still be processed.
* The single-file EXE is large (roughly 150-250 MB, it contains Qt and FFmpeg) and starts in a few seconds because it unpacks itself.
* The app has no payment features, so nothing is ever charged by Cartoon AI. Replicate bills your account directly.

## Adding another AI provider

Create `cartoon_ai/providers/yourprovider.py` with a class derived from `Provider` (see `base.py`): set `capabilities`, implement `configured()` and `run(req, report, cancelled)` (upload, create job, poll, download, return an MP4 path), then select it in `Ctx.active_provider()` in `context.py`.

## Project layout

```
run_cartoon.py            entry point
cartoon.spec              PyInstaller recipe (one-file Cartoon.exe)
.github/workflows/build-exe.yml   builds + self-tests the EXE on Windows
cartoon_ai/
  app.py  context.py  theme.py  art.py  widgets.py  dialogs.py  jobs.py
  ffmpeg_tools.py  db.py  config.py  secrets_store.py  styles_data.py  selftest.py
  providers/ base.py  replicate_provider.py  demo.py
  pages/     home studio styles_page editor creations settings_page about
```
