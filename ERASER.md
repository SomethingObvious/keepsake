# Remove Text

Remove Text takes captions, stickers, @usernames and watermarks off a picture by hand, the way a phone's magic eraser does, and saves a copy beside it. The original is never changed. It runs in Keepsake's own process on the processor, and needs two models, about 46 MB, that setup in Settings downloads.

## Using It

1. Open a picture in the library and press Remove Text, or T.
2. While the models load, the overlay network reads the whole picture at 512 px and marks in red what looks laid on top. Keep it, or take some off with the Eraser.
3. Paint over anything else that should go. When the pointer lifts, the stroke snaps to the text inside it. With Snap off, the mark is exactly what was painted.
4. Remove paints over everything marked. It can be pressed again on its own result, Undo steps back through strokes and removals, and Hold to Compare (or Space) shows the picture as it was.
5. Save Copy writes `<name> (no text)` beside the picture.

## How It Works

The code is `keepsake/eraser.py`, numpy and Pillow throughout, so the phone app can share it.

* **The snap.** The ring just outside a stroke is background, since a hand paints past the text. Its colours are clustered into eight, and a pixel inside the stroke is text when it is further from all eight than Otsu's threshold, and at least 20 RGB units away. Anything the overlay network sees as more than 30 % opaque counts too, read from the stroke's surroundings at up to 512 px. Small gaps close, so a white letter inside a dark outline stays whole, and the mark grows by a sixteenth of the stroke's thickness for anti-aliasing, outlines and shadows. It never goes past the stroke.
* **The fill.** MI-GAN's ONNX pipeline crops around a hole and paints it at 512 px. Holes within a 16 px block of each other are painted as one patch, with a quarter of the patch's size around it as context. Only marked pixels change.
* **Saving.** A JPEG is spliced rather than saved over: only the 8x8 blocks the edit touched are encoded, with the original's own quantisation tables and chroma sampling, and every other block keeps its exact coefficients, with the EXIF and colour profile. A photo turned by its EXIF orientation is edited upright and turned back for the splice. The phone app has no jpeglib, so there the whole JPEG is encoded again, with the original's own quantisation tables, chroma sampling, EXIF and colour profile. PNG and WebP are written losslessly, upright, with their transparency and colour profile.
* **The window.** The picture and every changed rectangle cross pywebview's bridge as `data:` addresses, and strokes go back as points, so no canvas reads pixels from a file.
* **Loading.** ONNX Runtime takes seconds to import, so it loads with both models on a thread of its own when the first picture opens, and stays loaded.

## What Was Measured

On 24 test pictures, 12 photos with Instagram-style captions, @usernames and watermarks, and the same 12 with coloured captions, outlined white captions and large see-through watermarks, with a capsule brushed along each line:

| Share of the overlay's ink left unmarked | Captions | Harder set |
| --- | --- | --- |
| Edge colours alone | 5.2 % | 1.9 % |
| The overlay network alone | 2.5 % | 20 % |
| Both, as shipped | 0.35 % | 1.2 % |

The mark covers about three quarters of what was brushed, so a quarter less is painted over. A stroke snaps in about 30 to 60 ms, Remove takes about 1.3 seconds a picture on a laptop's processor, and the first suggestion about 0.1 seconds. MI-GAN filled the same masks as well as the prototype it was chosen with (a median 14.6 dB inside the brush, against 14.3).

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
