# VeriSight — image checks with a trained model

VeriSight runs an experimental AI-image classifier locally and shows basic file checks separately. It does **not** yet detect face swaps, localized edits, video deepfakes, or cloned voices.

## Deploy on Vercel

The root `vercel.json` defines two services under one domain:

| Service | Public path | Runtime |
| --- | --- | --- |
| `frontend` | `/*` | Vite static site |
| `backend` | `/api/*` | Vercel container |

There are no service bindings because the browser calls the public `/api` route;
neither service makes a private server-side call to the other. Set the Vercel
project's Root Directory to `./` so it reads the root configuration. Do not set
`VITE_API_BASE_URL` for this same-domain deployment.

The Vercel container downloads a checksum-pinned Q8_0 release of the official Smaug
GGUF detector at build time and runs it with a pinned llama.cpp CPU runtime. The
original image and a JPEG copy each receive the publisher's full three-crop score.
The 128-pixel re-check is omitted in the compact runtime to stay within Hobby's
five-minute request limit. Local development keeps the float32 PyTorch runtime and
all three re-check versions.

Online uploads are capped at 4 MB to leave room below Vercel Functions' 4.5 MB
request-body limit. The Hobby plan has a five-minute maximum duration and 2 GB of
memory. The compact model used about 575 MiB peak working set in a one-image local
Windows test, but that is not a Vercel capacity guarantee. See
[Vercel function limits](https://vercel.com/docs/functions/limitations) and
[container runtime documentation](https://vercel.com/docs/functions/runtimes/container).

The first deployment downloads roughly 560 MB of pinned model/runtime artifacts
and may take several minutes. After deployment, `/api/v1/health` must report
`neural_detector: ready`. Idle production containers scale down, so the first
request after a quiet period can take longer. Add authentication and rate limits
before exposing CPU-intensive inference to unrestricted public traffic.

Model weights, virtual environments, local sample uploads, screenshots, environment
files, dependencies, and build output are excluded from Git. The container fetches
the compact model during its build; local clones use `setup-model.cmd` for PyTorch.

## Run

Open two terminals from the project root.

Backend:

```powershell
cd backend
npm run dev
```

Frontend:

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. Keep both terminals running; stop each with Ctrl+C. The backend uses its own `.venv` automatically, with code reload enabled. It requires Node but no `npm install` in `backend`.

If port 8000 is occupied by an older instance, stop that instance first. The frontend rejects old responses without model results instead of displaying a stale placeholder score.

## First-time installation

Python 3.11+ and Node are required. On Windows, from the root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..
.\setup-model.cmd
cd frontend
npm install
```

`setup-model.cmd` installs CPU PyTorch and the model libraries, then downloads pinned model weights (about 0.9 GB plus tokenizer files). This step needs internet access. Upload analysis uses local files only and does not upload images to Hugging Face. Model files live in `backend/models/smaug`, outside source control. Restart the backend after setup. The legacy root `.\verisight` launcher still works without reload. Allow roughly 1–2 minutes per image on CPU for the original and two re-checks; the frontend allows four minutes before timing out.

## What the result means

- Raw model output is available in expandable diagnostic details. It is **not calibrated probability**, accuracy, or proof of fakery.
- Automatic authenticity verdicts are disabled. The earlier 20/80 bands had no independent validation and have been removed. Completed inference returns `verdict: inconclusive`, `risk_score: null`, and `confidence: null`; the original output remains under `detection.ai_score` for evaluation.
- The page separately describes which class the model favored on the original image and each re-check. A raw AI-class output above 0.5 favors AI-generated; below 0.5 favors human-made; exactly 0.5 is a tie. These are descriptions of classifier output, not authenticity verdicts or confidence levels. Any class disagreement is shown, even if the score spread is below the provisional instability threshold.
- Failed, unavailable, and unsupported detection returns `ai_score: null` and no risk score. There is no fallback 8%.
- File metadata and texture heuristics do not change the model score.
- Each image is also re-checked after JPEG compression. The local PyTorch runtime adds a 128 × 128 resizing check; the compact Vercel runtime omits that slow third version. A class disagreement or score spread of 0.60 or more triggers a sensitivity warning. The original score is retained, not averaged with degraded copies. This provisional stability check does not catch all errors; consistent scores can also be wrong.
- Video, audio, animated images, and images smaller than 64 pixels per side receive no AI score.
- Results explain measured re-check scores, instability, and missing coverage. A classifier score cannot identify an eye, skin, lighting, or face-swap defect. No such visual explanation is fabricated. The list counts all displayed checks, including informational findings and unavailable capabilities.
- The application does not archive uploads. Multipart handling can use temporary OS files for large uploads, which are closed after reading.

## Regional measurements

Image reports now include `spatial_analysis`: four deterministic measurements on an EXIF-oriented, aspect-preserving analysis image capped at 1024 pixels on its longest side. An 8×8 grid records regional values. Transparent pixels are composited on white. Images below 64 pixels per side, animations, and non-images are explicitly unsupported; extreme aspect ratios can also be too narrow after scaling.

| Measurement | Calculation | What it does not establish |
| --- | --- | --- |
| Brightness variation | Regional mean of 0.2126R + 0.7152G + 0.0722B on display-encoded RGB; card shows regional P90–P10 gap | Light direction, shadow geometry, or lighting forgery |
| Texture | 32-bin regional Shannon entropy (0–5 bits); card shows median | Whether texture came from AI rather than natural material |
| Fine-detail / noise residual | Regional RMS residual after Gaussian smoothing (sigma 1, 7-tap kernel, replicated edges); card shows median | Sensor noise, camera identity, or a face swap |
| JPEG re-save difference | Regional mean absolute RGB difference after quality-90 JPEG re-save, no chroma subsampling | An editing history or pasted-object localization |

The maps use each image's own minimum and maximum, so colors cannot be compared as risk levels across images. Selecting a region shows its measured value and distance from the median. These measurements never alter the model output or authenticity verdict. Downloaded JSON reports include all 64 values per metric, methods, limitations, working resolution, and a small image preview; this preview contains image content, so review reports before sharing. Uploads and previews are not archived by the backend.

Synthetic tests cover uniform images, brightness steps, localized noise, orientation, unsupported inputs, and API serialization. They establish calculation behavior, **not deepfake-detection accuracy**. A benchmark measuring actual false positives and misses on independently labeled manipulations is still required.

Background: [Shannon entropy documentation](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.shannon_entropy); [lighting-forensics research](https://people.csail.mit.edu/kimo/publications/lighting/lighting.html). The lighting research estimates illumination under geometric assumptions; the brightness map here does not implement that method.

## Image classifier

[Abacus.AI Smaug AI Image Detector](https://huggingface.co/abacusai/Smaug-AI-Image-Detector), Apache-2.0, revision `c7c95951e04a87b884a4ad479401b1128c3903bd`.

Uses the supplied Sentence Transformers classification head and processor. The local runtime adapts the publisher's inference procedure: EXIF orientation, RGB, aspect-preserving scaling (shorter side capped at 576 or raised to 528), three 528 × 528 crops along the longer side, mean logits, then sigmoid. CPU inference uses float32 and batches one crop at a time. Original crop outputs and the aggregation method are included in downloaded reports. Inference is serialized. Only safetensors weights are loaded; remote code is disabled. Every downloaded model/config file is verified against a pinned SHA-256 at setup and startup. Startup health reports ready only after loading succeeds. Attribution and license are in `backend/licenses`.

The earlier SigLIP model missed the supplied AI building image with an AI-class output of 0.09/100. Smaug produced 95.57/100 on the original and 89.12/100 on its JPEG copy. The same image shrunk to 128 × 128 still failed (5.93/100); that disagreement remains visible. See `backend/evaluation/smaug-comparison.json` for the local development comparison, including genuine photographs and generated controls. This sample influenced model selection, so it is a regression case, not held-out evidence of general accuracy. There is no image-hash override or threshold tuned to this file.

Publisher benchmarks are not this application's accuracy. New generators, recompression, illustrations, small images, and content unlike training data may cause confident errors. No generator name is required from the user. This model still does not establish face-swap or localized-edit detection.

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m app.evaluate --download
```

The evaluation downloads three photographic examples from scikit-image and three generated examples from Hugging Face's Diffusers documentation. It evaluates originals, JPEG quality 85/50, and resized versions. All scores and hashes are saved in `backend/evaluation/smoke-results.json`. Subsequent runs can omit `--download`.

This six-example smoke check is **not** an independent benchmark: training overlap is unknown and transformations are correlated. Before claiming reliability, evaluate on a separate labeled dataset with unseen generators, faces and non-faces, screenshots, compression levels, and content groups. Report false positives and false negatives, then fit calibration only on a separate validation set.

For a labeled local dataset, create a CSV with columns `path,label,group,task`. Paths are relative to the CSV; labels are `real` or `fake`; tasks are `ai-generation` or `face-manipulation`. Group by source/generator/compression so aggregate scores cannot hide weak categories.

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.benchmark evaluation/my-test-set.csv --output evaluation/benchmark-results.json
```

This reports false-positive and false-negative rates, balanced accuracy, extreme outputs, failures, and coverage. Duplicate file bytes within a task are excluded and reported as failures. Face-manipulation samples are explicitly unsupported until a suitable detector is integrated. The tool uses a fixed 0.5 threshold for diagnostics only; running it never enables product verdicts. Labels and dataset independence require a separate audit. Split by original image/source identity before creating compressed copies; never use test data to choose models or tune thresholds. This command writes local paths and hashes to the report, so review it before sharing.

Frontend build: `cd frontend` then `npm run build`.

## API and deployment

- `GET /api/v1/health`: service and model readiness.
- `POST /api/v1/analyze`: multipart `file`; result includes model ID, revision, raw score, status, limitations, and file findings.
- API docs: http://localhost:8000/api/docs.

The optional Docker deployment serves the UI at http://localhost:8080. Run local model setup first; Compose mounts those model files read-only. No model is downloaded during container startup.
