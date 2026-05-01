# 4DGS-compression

## Prerequisites
- Install the dependencies:
    ```bash
    pip install plyfile numpy opencv-python
    ```

- Install ffmpeg: https://www.ffmpeg.org/
## CLI Usage

### Spatial compression
Encode a single PLY file into PNG textures:

```bash
python ply_encode_cli.py path/to/input.ply --out-dir path/to/output_dir --png-compression 9
```

Encode all PLY files in a folder (outputs are prefixed with FRAME_i_ in one directory):

```bash
python ply_encode_cli.py --ply-dir path/to/input_dir --out-dir path/to/output_dir --png-compression 9
```

Decode PNG textures back into a PLY file:

```bash
python ply_decode_cli.py --metadata path/to/metadata.json --textures-dir path/to/textures_dir --out-dir path/to/output_dir
```

### Spatiotemporal compression
Build H.264 videos from the per-frame textures (one video per texture group).

```bash
./encode_textures_to_h264.bat path/to/textures_dir path/to/output_videos 18 30
```

Parameters:
- `18` = H.264 CRF (quality). Lower means higher quality/larger files.
- `30` = frames per second for the output videos.
- Position textures (`xyz_0`, `xyz_1`) are encoded losslessly as FFV1 in `.mkv` files.

Decode H.264 videos back to PLYs:

```bash
python decode_videos_to_ply.py --videos-dir path/to/videos_dir --metadata-dir path/to/metadata_dir --out-dir path/to/output_dir
```

Parameters:
- `--videos-dir` = folder with per-group videos (xyz_0.mp4, color.mp4, etc).
- `--metadata-dir` = folder with FRAME_i_metadata.json files from encoding.
- `--out-dir` = where reconstructed PLYs are written.