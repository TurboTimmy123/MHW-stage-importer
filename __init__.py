import math
from glob import glob
from os.path import dirname, exists

import bpy
import bpy_extras
from bpy.props import BoolProperty, StringProperty

from .decode_ipr import DecodeIpr
from .decode_sobj import DecodeSobj

bl_info = {
    "name": "IPR Importer",
    "version": (1, 2, 0),
    "blender": (2, 79, 0),
    "author": "TurboTimmy123",
    "location": "File > Import-Export",
    "description": "Import MHW stage files",
    "category": "Import-Export",
}


class iprImportOperator(  # noqa: N801
    bpy.types.Operator,
    bpy_extras.io_utils.ImportHelper,
):
    bl_idname = "custom_import.import_ipr"
    bl_label = "Import stage"
    bl_options = {"REGISTER", "PRESET", "UNDO"}

    filename_ext = "*.ipr;*.bkipr;"
    filter_glob = StringProperty(
        default="*.ipr;*.bkipr;",
        options={"HIDDEN"},
        maxlen=255,
    )

    include_terrains = BoolProperty(
        name="Include terrains with IPR",
        default=True,
    )

    skip_ipr = BoolProperty(
        name="Skip IPR assets",
        default=False,
    )

    skip_sobj = BoolProperty(
        name="Skip SOBJ assets",
        description="Skip SOBJ assets associated with the stage",
        default=False,
    )

    bound_sobj = BoolProperty(
        name="Bound SOBJs",
        description="Only include SOBJ assets within the bounds of the IPRs zone, useful for large maps",
        default=False,
    )

    include_mats = BoolProperty(
        name="Include Materials",
        description="Include materials from the mod3 importer",
        default=True,
    )

    def execute(self, context):
        fp = self.properties.filepath

        # Get chunk dir from import IPR
        self.chunk_dir = fp[: fp.find("chunk") + 6]

        print(f"Using chunk dir: {self.chunk_dir}")

        self.stage_name = fp[fp.rfind("\\") + 1 :]
        self.scn = bpy.context.scene
        self.all_objects = []

        ipr_table = DecodeIpr(ipr_path=self.properties.filepath).transforms
        if not self.skip_ipr:
            print("Loading IPR assets...")
            for i, x in enumerate(ipr_table):
                print(
                    f"{i+1}/{len(ipr_table)} Importing: {x[x.rfind('/') + 1 :]} count:{len(ipr_table[x])}",
                )
                self.import_model(filename=x, trfs=ipr_table[x])

        if not self.skip_sobj:
            print("Loading SOBJ assets...")
            # Go up 2 parent folders
            # requires 3 dirnames as 1st trims filename
            stagedir = dirname(dirname(dirname(fp))) + "\\"

            if self.bound_sobj:
                xmin, ymin, zmin = (10e9,) * 3
                xmax, ymax, zmax = (-10e9,) * 3
                # Calculate bounds from ipr for sobj
                for objs in ipr_table:  # Iterate over every model...
                    for t in ipr_table[objs]:  # ...and every instance
                        # Skip bounds for terrains always at (0,0,0)
                        if t["pos"][0] == 0:
                            continue

                        if t["pos"][0] < xmin:
                            xmin = int(t["pos"][0])

                        if t["pos"][0] > xmax:
                            xmax = int(t["pos"][0])

                        if t["pos"][1] < ymin:
                            ymin = int(t["pos"][1])

                        if t["pos"][1] > ymax:
                            ymax = int(t["pos"][1])

                        if t["pos"][2] < zmin:
                            zmin = int(t["pos"][2])

                        if t["pos"][2] > zmax:
                            zmax = int(t["pos"][2])

                print("Importing within bounds:")
                print(f"x {xmin} -> {xmax}")
                print(f"y {ymin} -> {ymax}")
                print(f"z {zmin} -> {zmax}")
                padding = 500
                sobj = DecodeSobj(
                    stagedir=stagedir,
                    bounds=[
                        xmin - padding,
                        xmax + padding,
                        ymin - padding,
                        ymax + padding,
                        zmin - padding,
                        zmax + padding,
                    ],
                )
            else:
                sobj = DecodeSobj(stagedir=stagedir, bounds=None)

            sobj_table = sobj.transforms
            for i, x in enumerate(sobj_table):
                print(
                    f"{i+1}/{len(sobj_table)} Importing: {x} count:{len(sobj_table[x])}",
                )
                self.import_model(filename=x, trfs=sobj_table[x])

        if self.include_terrains:
            print("Loading terrains...")
            terrains = []

            if "title" in fp:
                # Terrain mods are in same dir as the .ipr, or in sdl
                modpath = fp[: fp.rfind("\\") + 1] + "**\\*.mod3"
                terrains += glob(pathname=modpath, recursive=True)
            elif fp[-5:] == "bkipr":
                # If loading a bkipr, go up 2 dirs
                modpath = fp[: fp.rfind("\\") + 1] + "..\\..\\**\\*.mod3"
                terrains += glob(pathname=modpath, recursive=True)
            elif fp[-3:] == "ipr":
                # Most terrains exist in parent directory mod3
                modpath = fp[: fp.rfind("etc")] + "mod\\*.mod3"
                terrains = glob(pathname=modpath, recursive=True)

            scene_before = set(bpy.data.objects)
            for i, t in enumerate(terrains):
                print(f"{i+1}/{(len(terrains))} {t}")
                bpy.ops.custom_import.import_mhw_mod3(
                    filepath=t,
                    clear_scene=False,
                    maximize_clipping=False,
                    import_textures=self.include_mats,
                    import_materials=self.include_mats,
                    import_skeleton="None",
                )
            self.all_objects.append(set(bpy.data.objects) - scene_before)

        self.apply_empty_parent()
        print("Velkhana best monster")
        return {"FINISHED"}

    def import_model(self, filename: str, trfs: list) -> None:
        fullpath = self.chunk_dir + filename + ".mod3"

        if not exists(fullpath):
            print("Missing file!!!")
            return

        scene_before = set(bpy.data.objects)
        bpy.ops.custom_import.import_mhw_mod3(
            filepath=fullpath,
            clear_scene=False,
            maximize_clipping=False,
            import_textures=self.include_mats,
            import_materials=self.include_mats,
            import_skeleton="None",
        )

        # Unfortunately we do not get a reference back
        # Compare scene before/after to get all imported objects
        objs = set(bpy.data.objects) - scene_before

        for o in objs:
            if "Armature" in o.name:
                continue

            self.apply_transforms(o, trfs[0])
            if len(trfs) > 1:
                # For all instances
                for i in range(1, len(trfs)):
                    new_obj = o.copy()
                    self.scn.objects.link(new_obj)
                    self.apply_transforms(new_obj, trfs[i])

        # Keep track of all objects for current import
        self.all_objects.append(set(bpy.data.objects) - scene_before)

    def apply_transforms(self, obj: list, trfs: list) -> None:
        obj.location = trfs["pos"]
        obj.scale = trfs["scl"]
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = trfs["rot"]

    # Applies everything to an empty parent, and apply a transform fix
    def apply_empty_parent(self) -> None:
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        empty = bpy.context.selected_objects[0]
        empty.name = self.stage_name.rsplit(".", 1)[0]
        # Preferably don't use ops but oh well :)
        # Probably better way to do this lol
        bpy.ops.object.select_all(action="DESELECT")
        for objs in self.all_objects:
            for o in objs:
                o.select = True
        bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)
        empty.rotation_euler[0] = math.radians(90)
        empty.scale[0] = 0.01
        empty.scale[1] = 0.01
        empty.scale[2] = 0.01


def menu_func_import(self, context) -> None:
    self.layout.operator(iprImportOperator.bl_idname, text="MHW Stage (.ipr/.bkipr)")


def register() -> None:
    bpy.utils.register_class(iprImportOperator)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister() -> None:
    bpy.utils.unregister_class(iprImportOperator)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
