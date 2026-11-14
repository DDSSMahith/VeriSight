"""Local inference following Abacus.AI's published three-crop Smaug procedure.

Source (Apache-2.0): abacusai/Smaug-AI-Image-Detector, revision
c7c95951e04a87b884a4ad479401b1128c3903bd, smaug_image_detect.py.
"""

import math

from PIL import Image, ImageOps


def image_views(image: Image.Image) -> list[Image.Image]:
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    if min(width, height) > 576:
        scale = 576 / min(width, height)
        image = image.resize(
            (round(width * scale), round(height * scale)), Image.Resampling.LANCZOS
        )
    elif min(width, height) < 528:
        scale = 528 / min(width, height)
        image = image.resize(
            (math.ceil(width * scale), math.ceil(height * scale)), Image.Resampling.BICUBIC
        )
    width, height = image.size
    cx, cy = (width - 528) // 2, (height - 528) // 2
    if width >= height:
        return [image.crop((x, cy, x + 528, cy + 528)) for x in (0, cx, width - 528)]
    return [image.crop((cx, y, cx + 528, y + 528)) for y in (0, cy, height - 528)]


class SmaugRuntime:
    def __init__(self, model_dir):
        import torch
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            str(model_dir),
            device="cpu",
            local_files_only=True,
            trust_remote_code=False,
            config_kwargs={"audio_config": None},
            model_kwargs={"torch_dtype": torch.float32, "use_safetensors": True},
        )
        processor = self.model[0].processor.image_processor
        processor.max_soft_tokens = processor.image_seq_length = 140
        self.model.eval()

    def predict(self, image: Image.Image) -> tuple[float, list[float]]:
        import torch

        with torch.inference_mode():
            logits = (
                self.model.encode(
                    [{"image": crop} for crop in image_views(image)],
                    batch_size=1,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                )
                .float()
                .reshape(-1)
            )
            if logits.shape != (3,) or not torch.isfinite(logits).all():
                raise ValueError("Invalid classifier output")
            # Mean logits is the publisher's rule; never cherry-pick a crop's maximum.
            return torch.sigmoid(logits.mean()).item(), torch.sigmoid(logits).tolist()
