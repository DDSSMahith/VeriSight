from PIL import Image

from app.detectors.smaug_runtime import image_views


def test_wide_image_views_cover_both_ends_without_stretching():
    image = Image.new("RGB", (1200, 550), "black")
    image.paste("red", (0, 0, 20, 550))
    image.paste("blue", (1180, 0, 1200, 550))
    views = image_views(image)
    assert [view.size for view in views] == [(528, 528)] * 3
    assert views[0].getpixel((0, 0)) == (255, 0, 0)
    assert views[1].getpixel((0, 0)) == (0, 0, 0)
    assert views[2].getpixel((527, 0)) == (0, 0, 255)


def test_small_portrait_has_three_valid_views():
    views = image_views(Image.new("RGB", (64, 128), "gray"))
    assert all(view.size == (528, 528) for view in views)
