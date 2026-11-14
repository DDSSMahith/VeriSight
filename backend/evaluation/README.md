# Local model check

## Current model: Smaug

`smaug-comparison.json` contains the November 14 replacement-model comparison:
seven originals, each with a JPEG-quality-85 copy and a 128 × 128 copy. At the
unchanged 0.5 class boundary, all seven originals and seven JPEG copies matched
their labels. Only three of seven tiny copies matched; all three genuine photos
became false positives and the supplied building image became a false negative.
These are counts on development examples, **not an accuracy estimate**.

The building's AI label is user-reported; its generator is unknown. The other six
images use the public sources below. Scores, hashes, and model revision are saved.
No filename/hash rules or sample-specific threshold changes are used by inference.
Model selection used these examples, so a new, independently labeled dataset is
required for validation. Correlated transformations cannot count as independent samples.

The old classifier gave the building 0.09/100. Smaug gives the original 95.57/100,
JPEG copy 89.12/100, and tiny copy 5.93/100. These are raw AI-class outputs, not
confidence. `building-smaug-api.json` records the actual upload response through
the frontend proxy, including crop outputs, measurements, and explanations.

The development comparison initially used the reviewed publisher wrapper. The
production runtime implements the same three-crop/mean-logit procedure and is
checked against that result through the API. To repeat using the local runtime:

```powershell
cd backend
.\.venv\Scripts\python.exe evaluation/compare_smaug.py
```

Use existing ignored samples in `evaluation/samples`; the command does not
download images. Allow about ten minutes on CPU. The supplied image is a local
regression fixture and is not committed. No broad deepfake-detection or
face-manipulation claim follows from this comparison.

Other local candidates were rejected: TensorFold Detectra missed the building;
Detectra OpenFake caught it but mislabeled the real astronaut original. The latter
was evaluated locally only (CC-BY-NC); it is not part of the application's runtime.
Their comparison JSON files retain the observed results.

## Historical SigLIP baseline

The saved smoke-results.json is a historical run from before automatic authenticity verdicts were disabled. Its verdict labels are not the current application policy. Raw measurements remain useful for reproducing the model's failure. Current reports abstain and keep model output in diagnostic details.

See `smoke-results.json` for all six originals and eighteen transformed variants, with source URLs, file hashes, raw outputs, and stability checks.

Observed on this machine:

- The camera and cat photographs received very low AI scores.
- Three generated examples from Diffusers documentation received high AI scores.
- The real astronaut photograph changed from about 23.6/100 to 99.96/100 after JPEG compression. The stability check flagged the original and both compressed copies as unreliable and returned an inconclusive verdict.

This failure is material. A high raw score alone is not enough to call an image fake. The added JPEG/resizing check caught this particular error but does not guarantee that other false positives will be caught.

This is a small smoke test, not a representative held-out benchmark. Training overlap is unknown. The transformed copies are not independent samples. No calibrated probabilities or general accuracy claims are supported by this experiment. Model selection and thresholds were informed by these examples, so future validation must use separate data.

Sources:

- Photographs: scikit-image v0.24.0 sample data (astronaut, camera, chelsea).
- Generated images: https://huggingface.co/docs/diffusers/using-diffusers/conditional_image_generation
- Model card: https://huggingface.co/Ateeqq/ai-vs-human-image-detector

Run `python -m app.evaluate --download` from `backend` in its environment; omit `--download` to reuse the files offline. Downloaded examples are ignored by Git.

## Requirements before enabling verdicts

The target includes both fully AI-generated images and manipulated faces. These must have separate coverage and error-rate reports. The current model covers only the first task experimentally; no face-swap model is installed.

Use `python -m app.benchmark <manifest.csv> --output <report.json>` to measure labeled local data. Include genuine camera photos, generated images from unseen generators, genuine face crops and known manipulated faces, and held-out compression/screenshot variants. Keep related versions and identities in the same split. Audit label provenance and training overlap. Fit any calibration or thresholds on a separate validation set, then freeze them before final testing. Stable outputs are not proof of accuracy.

Research candidates require evaluation before integration:

- AI generation: [UniversalFakeDetect](https://github.com/WisconsinAIVision/UniversalFakeDetect) provides a research model and evaluation code. It is not a guarantee on present-day generators.
- Face manipulation: [DeepfakeBench](https://github.com/SCLBD/DeepfakeBench) supplies detector implementations and benchmark protocols. Correct face cropping, trained detector weights (not just ImageNet backbones), license terms, and cross-dataset testing must be checked before deployment.

Smaug is now installed for AI-generation checks, based on the development comparison
above. No face-manipulation candidate has been installed or validated. Independent
validation remains outstanding for both tasks.
