## im-scale-convert

`im-scale-convert` scales batches of images and optionally converts them to WebP using Pillow's high-quality resampling. The CLI is designed for quick automation of common image resizing workflows.

### Installation

Install from a local checkout or GitHub URL with `pip`/`uv`:

```bash
uv pip install git+https://github.com/robert-mcdermott/im-scale-convert.git
```

Or run directly via `uvx` without installing globally:

```bash
uvx im-scale-convert --percent 50 --input-dir images --output-dir images-scaled
```

To run straight from a Git repository without cloning:

```bash
uvx --from git+https://github.com/robert-mcdermott/im-scale-convert.git im-scale-convert --percent 60 \
  --input-dir images --output-dir images-scaled
```

### Usage

```bash
im-scale-convert --percent 60 --input-dir images --output-dir images-scaled \
  --optimize --strip-metadata
```

#### Common examples

- Scale images by 60% into `images-scaled` while optimizing and stripping metadata:
  ```bash
  im-scale-convert --percent 60 --input-dir images --output-dir images-scaled \
    --optimize --strip-metadata
  ```

- Convert PNG/JPEG sources to WebP during scaling:
  ```bash
  im-scale-convert --percent 60 --input-dir images --output-dir images-webp \
    --to-webp --quality 85
  ```

- Produce lossless WebP outputs:
  ```bash
  im-scale-convert --percent 60 --input-dir images --output-dir images-webp \
    --to-webp --webp-lossless
  ```

### Options

- `--percent`, `-p` (required): Scale percent, such as `50` for 50%.
- `--input-dir`: Directory to scan for supported images (default: `images`).
- `--output-dir`: Destination directory for resized images (default: `images-scaled`).
- `--quality`: Quality parameter for JPEG/WEBP (default: `85`).
- `--optimize`: Enable lossless optimizations for JPEG/PNG outputs.
- `--strip-metadata`: Remove EXIF/ICC metadata for smaller file sizes.
- `--to-webp`: Convert all outputs to WebP.
- `--webp-lossless`: Write lossless WebP images (quality is ignored).
- `--workers`: Number of worker threads (default: CPU count).

Supported inputs: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`.

### Development

Run the CLI locally for development and testing:

```bash
uv run im_scale_convert/cli.py --percent 50 --input-dir images --output-dir images-scaled
```

To package for distribution, build via `uv build` or `python -m build`, then upload to PyPI.
