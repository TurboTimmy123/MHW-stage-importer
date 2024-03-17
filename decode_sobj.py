import math
import re
import struct
from glob import glob
from os.path import exists

from mathutils import Euler


def get_name(f) -> str:
    n = ""
    is_char = True
    while is_char:
        tmp = str(struct.unpack("c", f.read(1))[0].decode("utf-8"))
        if str(tmp).isalnum() or str(tmp) == "_" or str(tmp) == "\\":
            n += tmp
        else:
            is_char = False
    return n


class DecodeSobj:
    def __init__(self, stagedir: str, bounds: list) -> None:
        self.bounds = bounds
        self.stagedir = stagedir
        self.chunk_dir = self.stagedir[: self.stagedir.find("chunk") + 6]
        self.stageSetPath = stagedir + "common\\set\\"
        self.GMList = self.generate_gm_list()
        self.totalCount = 0
        self.transforms = {}

        sobjs = glob(self.stageSetPath + "*.sobj", recursive=True)
        for s in sobjs:
            self.decode_gm_sobj(gm_sobj_path=s)

    def bound_check(self, x: float, y: float, z: float) -> bool:
        # Order: [xmin, xmax, ymin, ymax, zmin, zmax]
        if (
            (x < self.bounds[0])
            or (x > self.bounds[1])
            or (y < self.bounds[2])
            or (y > self.bounds[3])
            or (z < self.bounds[4])
            or (z > self.bounds[5])
        ):
            return False
        return True

    def read_float(self, f) -> float:
        return struct.unpack("f", f.read(4))[0]

    def decode_gm_sobj(self, gm_sobj_path: str) -> None:
        f = open(gm_sobj_path, "rb")

        data = f.read().decode("latin-1")

        gm_regex = re.compile("cAssetBasicSetObject")
        for i in gm_regex.finditer(data):
            offset = i.start()
            f.seek(offset + 25)

            x = self.read_float(f)
            y = self.read_float(f)
            z = self.read_float(f)
            rx = self.read_float(f)
            ry = self.read_float(f)
            rz = self.read_float(f)
            sx = self.read_float(f)
            sy = self.read_float(f)
            sz = self.read_float(f)

            # Skip asset if bounds used and outside
            if (self.bounds is not None) and (not self.bound_check(x, y, z)):
                continue

            name = get_name(f)
            name = self.find_nearest_gm(file_name=name)

            # Found no valid mod references, skip
            if name is None:
                continue

            # Trim path and extension
            name = name[len(self.chunk_dir) : -5]
            # Euler to Quaternion, for consistency, not because I like it xD
            # rot = Rotation.from_euler("xyz", [rx, ry, rz], degrees=True).as_quat()
            rot = Euler(
                (math.radians(rx), math.radians(ry), math.radians(rz)),
            ).to_quaternion()

            keydata = {
                "pos": [x, y, z],
                "scl": [sx, sy, sz],
                "rot": [rot[0], rot[1], rot[2], rot[3]],
            }

            if name in self.transforms:
                self.transforms[name].append(keydata)
            else:
                self.transforms[name] = [keydata]

            self.totalCount += 1

    # Returns an array of all GM paths
    def generate_gm_list(self) -> list:
        gms = []
        globcmd = self.chunk_dir + "Assets\\**\\*gm*.mod3"
        gms += glob(pathname=globcmd, recursive=True)
        globcmd = self.chunk_dir + "vfx\\**\\*gm*.mod3"
        gms += glob(pathname=globcmd, recursive=True)
        globcmd = self.chunk_dir + "stage\\**\\*gm*.mod3"
        gms += glob(pathname=globcmd, recursive=True)
        globcmd = self.chunk_dir + "common\\**\\*gm*.mod3"
        gms += glob(pathname=globcmd, recursive=True)
        return gms

    # Sometimes this GM path is a mod3 path,
    # othertimes a .gma which reference the mod3 path, idk
    # Sometimes also requires _## to be removed, idk why lol
    def find_nearest_gm(self, file_name: str) -> str:
        for i in self.GMList:
            if file_name + ".mod3" in i:
                return i

        # Try delete _00
        for i in self.GMList:
            if file_name[:-3] + ".mod3" in i:
                return i

        tmp = self.parse_gma(gma_name=file_name)
        if tmp:
            return tmp

        tmp = self.parse_gma(gma_name=file_name[:-3])
        if tmp:
            return tmp

        return None

    # These are only present for st101 -> st109, st403, st409
    def parse_gma(self, gma_name: str) -> str:
        stage_id = self.stagedir[self.stagedir[:-1].rfind("\\") + 1 : -1]
        gma_path = self.chunk_dir + "Assets\\gm\\" + stage_id + "\\" + gma_name + ".gma"
        if not exists(gma_path):
            return None

        f = open(gma_path, "rb")
        data = f.read().decode("latin-1")
        gm_regex = re.compile("Assets")
        gm_name = []
        # Find all asset references in .gma
        for i in gm_regex.finditer(data):
            offset = i.start()
            f.seek(offset)
            tmp = get_name(f)
            if "\\col\\" not in gm_name:
                gm_name.append(tmp)
        # Mod3 path will be the shortest result
        return self.chunk_dir + min(gm_name, key=len) + ".mod3"


if __name__ == "__main__":
    test = "D:\\MHW_Chunk\\chunk\\stage\\st101\\"
    d = DecodeSobj(test, None)
