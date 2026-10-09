# Removing Added Text

The text remover takes text that was laid over a picture (captions, story text, stickers, @usernames, watermarks) off it, and leaves text that belongs to the picture (signs, shirts, packaging, a poster, a book's own cover). When it is unsure it leaves the text, since a caption left behind is a nuisance and a sign rubbed out is damage. Pressed in the library, it saves a cleaned copy beside the picture. Turned on for downloads, the cleaned picture takes the original's place and the original goes to the Recycle Bin.

## How It Works

1. PP-OCRv6 finds every line of text, on the processor.
2. The overlay network (`overlay.onnx`, 4.6 M parameters, about a second on a processor) gives two opacity maps for the whole picture, hard for glyphs, plates and stickers, and soft for shadows and glows. It was trained to leave scene text at zero.
3. A line goes only when two separate checks say it was added. One is the network covering the line (`COVERED` in `pipeline.py`), and the other is a judge asked about every line of the picture, small on the processor in the quick tier and large on the graphics card in the best tier. The network alone is not enough, as flat, sharp signage such as a marquee or a book cover's title looks to it like a sticker.
4. A caption goes whole or not at all. A line next to one the checks disagreed on stays too. A band of a fifth of a line's height is painted around each glyph, since a missed drop shadow would stay as a ghost of the letters.
5. The picture is rebuilt one kind of pixel at a time (`layers.py`). Where the overlay is opaque, LaMa (quick) or FLUX.2 [klein] 4B (best) paints in what was under it. Where it is see-through, the photo is still there, so it is un-blended with `photo = (pixel - alpha * colour) / (1 - alpha)`. Thin see-through strokes are painted instead, since un-blending multiplies JPEG's error.
6. The cleaned picture is read for text too. A removed line that still reads is reported, and a scene line that reads differently gets its pixels put back.
7. A JPEG is spliced rather than saved over. Only the 8x8 blocks the edit touched are encoded, with the original's own quantisation tables, and its EXIF and colour profile stay. PNG and WebP are written losslessly.

## What Was Measured

On an 8 GB RTX 4070 Laptop, against 14 photos with Instagram-style overlays in fonts the network never saw, their clean originals, 16 OTR-hard samples (CyberAgent's overlay text benchmark, ACM MM 2025) and 16 held-out Wikimedia photos full of real signage:

* A mask that follows the glyphs beat a box around the line by 7 dB on OTR with the same painter. The box wiped out a doll's eye.
* FLUX.2 [klein] paints large holes far better than LaMa, which smears and leaves grey blotches, and it keeps what surrounds the hole.
* Un-blending beats painting wherever the overlay is see-through. On a 67 % black plate the error fell from 23.5 to 6.7, which is about the floor JPEG's noise allows.
* The network alone is not safe. Overlay lines cover a median 0.44 of their box, but real signage reaches 0.79, so no threshold separates them.
* The large judge got 268 of 270 lines right on its own. With the network, the small judge removed no scene text across 41 flagged pictures and took off 31 of their 64 overlay lines, at a median 8 seconds a picture.
* The best tier also asks whether a picture is itself a piece of graphic design, and leaves a design alone. That saves a book cover's title, though it also leaves about a dozen heavily captioned memes as they are.

The network that ships was trained without the Total-Text photos, whose terms allow academic research only. Through the quick tier it cleaned 32 of 90 test pictures with overlays (34 for the network measured above) and touched none of 30 photos of real signage.

## The Two Tiers

| | Quick | Best |
| --- | --- | --- |
| Runs on | any computer, the processor | an NVIDIA card with 8 GB |
| Paints with | LaMa, in 512 px tiles | FLUX.2 [klein] 4B, in crops around each hole |
| Download | about 2.3 GB | about 28 GB |
| Time | a few seconds a picture, 10 to 60 with text to judge | about half a minute a picture |

## The Network

A U-Net on a MobileNetV3-Large encoder, started from torchvision's ImageNet weights, with a full-resolution branch for 1 px edges. It was trained for 16,000 steps on 16,000 synthetic pictures: backgrounds from 4,908 TextOCR photos and OTR's clean images, overlays drawn the way Instagram and TikTok draw theirs in 33 fonts the tests never use, OTR's own training pairs, and a third of the pictures with no overlay at all. The training scripts are not part of the program. Setup downloads the network from this repository, pinned to a tag and checked against its hash.

## Limits

* Pictures only (JPEG, PNG, WebP), never video.
* A caption on a coloured band added around a photo loses its text, but the band stays.
* It is conservative by design. The quick tier took off about half of the overlay lines in the tests and no scene text, and it leaves memes and multi-line captions it is unsure of.

## Credits

The network learned from TextOCR (Singh and others, CVPR 2021), whose annotations are under CC BY 4.0 and whose photos come from Open Images under CC BY 2.0, and from OTR (Zdenek, Shimoda and Yamaguchi, ACM Multimedia 2025, CyberAgent) under CC BY 4.0. Its overlays were drawn in Google Fonts (SIL Open Font License and Apache 2.0) and fonts that come with Windows, and its encoder started from torchvision's ImageNet weights (BSD 3-Clause). The network itself is under Keepsake's MIT licence.

What setup downloads beside it keeps its own licence, and each one allows this use. PP-OCRv6 through RapidOCR, LaMa, Qwen3.5-2B and 9B (the judges) and FLUX.2 [klein] 4B are under Apache 2.0, and llama.cpp, which runs the judges, is under MIT.
