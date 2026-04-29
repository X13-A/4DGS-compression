# 4DGS-compression

## Prerequisites
- Install micromamba
- Clone "Self-Organizing-Gaussians": https://github.com/fraunhoferhhi/Self-Organizing-Gaussians.git

## PLY Inspector
Install the dependency:

```bash
pip install plyfile numpy opencv-python
```

Encode a PLY file into PNG textures:

```bash
python ply_encode_cli.py Gaussians_Chicago_Bus_60/bus_0.ply --out-dir outputs
```

Decode PNG textures back into a PLY file:

```bash
python ply_decode_cli.py --metadata outputs/bus_0_metadata.json --textures-dir outputs --out-dir reconstructed
```

