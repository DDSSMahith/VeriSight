# Smaug inference attribution

`app/detectors/smaug_runtime.py` adapts the image preprocessing and logit aggregation
from Abacus.AI's `smaug_image_detect.py`, published with the Smaug AI Image Detector
under Apache License 2.0.

Source: https://huggingface.co/abacusai/Smaug-AI-Image-Detector/blob/c7c95951e04a87b884a4ad479401b1128c3903bd/smaug_image_detect.py

Changes: local-only model loading, remote code disabled, safetensors required,
CPU float32 with batch size one, finite-output validation, and per-crop outputs.
The original license is preserved in `Smaug-Apache-2.0.txt`.
