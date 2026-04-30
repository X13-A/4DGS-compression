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
python ply_encode_cli.py --ply-dir data_bus --out-dir outputs --png-compression 9
```

Decode PNG textures back into a PLY file:

```bash
python ply_decode_cli.py --metadata outputs/bus_0/bus_0_metadata.json --textures-dir outputs/bus_0 --out-dir reconstructed/bus_0
```