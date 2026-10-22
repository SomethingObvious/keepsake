# Remove Text

Remove Text takes captions, stickers, @usernames and watermarks off a picture by hand, the way a phone's magic eraser does, and saves a copy beside it. The original is never changed. It runs in Keepsake's own process on the processor, and needs two models, about 46 MB, which its button offers to download the first time, as does Settings.

## Using It

1. Open a picture in the library and press Remove Text, or T.
2. While the models load, the overlay network reads the whole picture at 512 px and marks in red what looks laid on top, snapped as a stroke over it would be. Keep it, or take some off with the Eraser.
3. Paint over anything else that should go. When the pointer lifts, the stroke snaps to the text inside it. With Snap off, the mark is exactly what was painted. Two fingers, or Ctrl and the wheel, zoom in; the brush keeps its size on screen, so it paints finer.
4. Remove paints over everything marked. It can be pressed again on its own result, Undo steps back through strokes and removals, and Hold to Compare (or Space) shows the picture as it was.
5. Save Copy writes `<name> (no text)` beside the picture.

## How It Works

The code is `keepsake/eraser.py`, numpy and Pillow throughout, so the phone app can share it.

* **The snap.** Precision comes before recall: missing a little text is fixed by painting again, and painting over what is not text is not fixed at all. The ring just outside a stroke is background, since a hand paints past the text. Its colours are clustered into eight, and a pixel inside the stroke may be text when it is further from all eight than Otsu's threshold, and at least 20 RGB units away. It counts only within 3 px of what the overlay network sees as more than 30 % opaque, read from the stroke's surroundings at up to 512 px: colour knows exactly where an edge is and the network whether it is text, so a dark tree or a bright edge that a loose stroke crossed stays. The mark grows 2 px for the anti-aliased edge the fill must cover, and never goes past the stroke. The first suggestion is the network's view painted roughly, as a hand would, and snapped the same way.
* **The fill.** MI-GAN's ONNX pipeline crops around a hole and paints it at 512 px. Holes within a 16 px block of each other are painted as one patch, with a quarter of the patch's size around it as context. Only marked pixels change.
* **Saving.** A JPEG is spliced rather than saved over: only the 8x8 blocks the edit touched are encoded, with the original's own quantisation tables and chroma sampling, and every other block keeps its exact coefficients, with the EXIF and colour profile. A photo turned by its EXIF orientation is edited upright and turned back for the splice. The phone app has no jpeglib, so there the whole JPEG is encoded again, with the original's own quantisation tables, chroma sampling, EXIF and colour profile. PNG and WebP are written losslessly, upright, with their transparency and colour profile.
* **The window.** The picture and every changed rectangle cross pywebview's bridge as `data:` addresses, and strokes go back as points, so no canvas reads pixels from a file.
* **Loading.** ONNX Runtime takes seconds to import, so it loads with both models on a thread of its own when the first picture opens, and stays loaded.

## What Was Measured

On 12 public-domain photographs (NASA's), each with an outlined white caption, coloured words, an @username and a see-through watermark, and a loose stroke over each: a brush 1.5 to 2 times the text's height, running past both ends and wobbling. Marked but not text counts what lies more than 3 px from the text:

| 48 strokes | Marked, but not text | Text covered |
| --- | --- | --- |
| The snap before 1.4.4 | 770,746 px, 42.5 % of the mark | 693,744 of 693,835 px, 100 % |
| The snap now | 25,809 px, 3.2 % of the mark | 609,367 of 693,835 px, 87.8 % |

Before, the edge colours and the network were added together, small gaps were closed and the mark grew by a sixteenth of the brush's thickness, about 9 px for a loose stroke, and those last two made two thirds of what was marked wrongly. Captions, coloured words and usernames are now covered in full or nearly (98 % to 100 %, with 0.8 % to 1.8 % of the mark astray); the see-through watermark is where coverage goes, at 64 %, since its colour is mostly the photo's. On the same pictures the first suggestion now marks 176,335 px that are not text, against 905,268, and covers 67 % of the text, against 85 %.

A stroke snaps in about 30 to 60 ms, Remove takes about 1.3 seconds a picture on a laptop's processor, and the first suggestion about 0.1 seconds. MI-GAN filled the same masks as well as the prototype it was chosen with (a median 14.6 dB inside the brush, against 14.3).

## Limits

* Pictures only (JPEG, PNG, WebP), never video.
* MI-GAN paints at 512 px, so a large patch on a big picture comes out softer than the photo around it.
* A see-through watermark is painted over, not recovered: what was under it is invented.
* The first suggestion finds captions and stickers better than faint watermarks, which are painted by hand.

## The Network

A U-Net on a MobileNetV3-Large encoder (4.6 M parameters) that gives two opacity maps, hard for glyphs, plates and stickers, and soft for shadows and glows. It was trained to leave scene text at zero, on 16,000 synthetic pictures: backgrounds from TextOCR photos and OTR's clean images, overlays drawn the way Instagram and TikTok draw theirs in 33 fonts, OTR's own training pairs, and a third with no overlay at all. Setup downloads it from this repository, pinned to the tag in `textremoval.NETWORK_TAG` and checked against its hash.

## Credits

The network learned from TextOCR (Singh and others, CVPR 2021), whose annotations are under CC BY 4.0 and whose photos come from Open Images under CC BY 2.0, and from OTR (Zdenek, Shimoda and Yamaguchi, ACM Multimedia 2025, CyberAgent) under CC BY 4.0. Its overlays were drawn in Google Fonts (SIL Open Font License and Apache 2.0) and fonts that come with Windows, and its encoder started from torchvision's ImageNet weights (BSD 3-Clause). The network itself is under Keepsake's MIT licence.

MI-GAN is by Sargsyan, Navasardyan, Xu and Shi of Picsart AI Research ("MI-GAN: A Simple Baseline for Image Inpainting on Mobile Devices", ICCV 2023), and its code and weights are under the MIT licence. Setup downloads the ONNX pipeline from its first author's Hugging Face repository, which the official repository links to, pinned to a revision and checked against its hash.
