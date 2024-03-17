import struct


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


class DecodeIpr:
    def __init__(self, ipr_path: str) -> None:
        print(f"Opening {ipr_path}")
        self.path = ipr_path
        f = open(self.path, "rb")

        # File format check
        header = f.read(4)
        if header[0:3] == b"ipr":
            filetype = "IPR"
        elif header[0:4] == b"bipr":
            filetype = "BIPR"
        else:
            print("Error parsing headers, unknown file")
            return

        # Get object count
        f.seek(72)
        objectcount = struct.unpack("I", f.read(4))[0]

        # Object header stuff starts now
        if filetype == "IPR":
            f.seek(112)
        else:  # BIPR
            f.seek(128)

        # Parse Header to get object offsets and count
        header = []
        for i in range(objectcount):
            data = f.read(64)
            temp = [struct.unpack("I", data[x : x + 4])[0] for x in range(0, 64, 8)]

            header.append(temp)
            # 64 byte gap
            if i != objectcount:
                f.read(64)

        self.transforms = {}
        for i in header:
            f.seek(i[0])
            name = get_name(f)
            self.transforms[name] = self.get_transforms(f=f, offset=i[6], count=i[7])

    # Given file offset and count, return dict of transforms
    def get_transforms(self, f, offset: int, count: int) -> list:
        f.seek(offset)
        modtable = []
        for _ in range(count):
            data = f.read(144)
            temp = [struct.unpack("f", data[x : x + 4])[0] for x in range(0, 144, 4)]

            pos = [temp[0], temp[1], temp[2]]
            scale = [temp[3], temp[4], temp[5]]
            rot = [temp[9], temp[6], temp[7], temp[8]]

            modtable.append({"pos": pos, "scl": scale, "rot": rot})
        return modtable


if __name__ == "__main__":
    test = "F:\\MHW_Chunk\\chunk\\stage\\st101\\st101_A\\etc\\st101_A.ipr"
    # test = "F:\\MHW_Chunk\\chunk\\stage\\st414\\common\\etc\\st414.bkipr"
    # test = "F:\\MHW_Chunk\\chunk\stage\\st101\common\\etc\\st101.bkipr"
    DecodeIpr(test)
