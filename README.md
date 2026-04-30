# 4DGS-compression

## Prerequisites
- Install micromamba
- Clone "Self-Organizing-Gaussians": https://github.com/fraunhoferhhi/Self-Organizing-Gaussians.git

## CLI Usage
Install the dependencies:

```bash
pip install plyfile numpy opencv-python
```

Encode a PLY file into PNG textures (xyz uses 16-bit PNG; other groups use 8-bit):

```bash
python ply_encode_cli.py data_bus/bus_0.ply --out-dir outputs/bus_0 --png-compression 9
```

Encode all PLY files in a folder (outputs are prefixed with FRAME_i_ in one directory):

```bash
python ply_encode_cli.py --ply-dir data_bus --out-dir outputs/bus_video --png-compression 9
```

Decode PNG textures back into a PLY file:

```bash
python ply_decode_cli.py --metadata outputs/bus_encoded_textures/FRAME_0_metadata.json --textures-dir outputs/bus_encoded_textures_FRAME_0 --out-dir reconstructed/bus_FRAME_0
```

## Video
Build H.264 videos from the per-frame textures (one video per texture group).

```bash
./encode_textures_to_h264.bat outputs/bus_video output_videos 18 30
```

Parameters:
- `18` = H.264 CRF (quality). Lower means higher quality/larger files.
- `30` = frames per second for the output videos.
- Position textures (`xyz_0`, `xyz_1`) are encoded losslessly as FFV1 in `.mkv` files.

Decode H.264 videos back to PLYs (in-memory, no texture files are written):

```bash
python decode_videos_to_ply.py --videos-dir output_videos --metadata-dir outputs/bus_video --out-dir reconstructed/bus_video
```

Parameters:
- `--videos-dir` = folder with per-group videos (xyz_0.mp4, color.mp4, etc).
- `--metadata-dir` = folder with FRAME_i_metadata.json files from encoding.
- `--out-dir` = where reconstructed PLYs are written.

## Sample dataset commands :
```bash
python ply_encode_cli.py --ply-dir data_bus --out-dir outputs/bus_encoded_textures --png-compression 9
```

```bash
./encode_textures_to_h264.bat outputs/bus_encoded_textures outputs/bus_encoded_videos 18 30
```

```bash
python decode_videos_to_ply.py --videos-dir outputs/bus_encoded_videos --metadata-dir outputs/bus_encoded_textures --out-dir reconstructed/bus
```