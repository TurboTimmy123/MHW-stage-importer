import os
import math
import glob
import bpy
import re
import bpy_extras
import struct
from bpy.props import StringProperty, BoolProperty, EnumProperty
from mathutils import Vector, Quaternion, Matrix


### Changelog
#
# - 1.0.0
# Initial proof of concept
#
# - 1.0.1
# Duplicate as instances instead of copies
#
# - 1.0.2
# Convert to Addon
#
# - 1.0.3
# Fixed menu stage terrains
# Omit missing files instead of fail
#
# - 1.0.4
# Rewrote IPR decoder
#
# - 1.1.0
# Added sobj support for cAssetBasicSetObject types


bl_info = {
    "name": "IPR Importer",
    "version": (1, 0, 4),
    "blender": (2, 79, 0),
    "author": "TurboTimmy123",
    "location": "File > Import-Export",
    "description": "Import MHW stage files",
    "category": "Import-Export"}

# Given a file or folder, and a target folder
# Look up recursively and return target path
def HuntUp(dir, folder):
    # If a file is specified
    # Get the directory
    if '.' in dir:
        dir = dir[:dir.rfind("\\")]
    
    if dir[-1] == '\\':
        dir = dir[:-1]
        
    print("dir: " + dir)
    
    # If folder is here
    for f in os.listdir(dir):
        if f == folder:
            return dir + "\\" + f
        
    # RECURSION FRICK YEAH
    return HuntUp(dir[:dir.rfind("\\")], folder)
    

def GetName(f):
    id = ""
    charString = True
    while charString:
        temp = str(struct.unpack('c', f.read(1))[0].decode("utf-8"))
        if str(temp).isalnum() or str(temp) == '_' or str(temp) == '\\':
            id += temp
        else:
            charString = False
    return id
   
    
    
class SOBJParser():
    def __init__(self, stageDir, cd):
        self.chunk = cd
        self.stageDir = stageDir
        self.stageSetPath = stageDir + "common\\set\\"
        self.GMList = self.GenerateGMList()
        
        sobjs = self.FindAllSOBJ(self.stageSetPath)
        self.transforms = {}
        for s in sobjs:
            self.Decode_gm_SOBJ(s)
        
        #for x in self.transforms:
        #    print(str(x) + " " + str(self.transforms[x]))
        
        
        #for gms in transforms:
        #    temp = self.FindNearestGMMatch(gms)
        #    print("gms: " + gms)
        #    print(temp)
            

    def FindAllSOBJ(self, stage_set_path):
        sobjs = []
        for f in glob.glob(stage_set_path + "*.sobj"):
            sobjs.append(f)
        return sobjs

        
    def Decode_gm_SOBJ(self, gm_SOBJ_path):
        print("Decoding " + gm_SOBJ_path)
        f = open(gm_SOBJ_path, 'rb')
        
        #f.seek(20)
        #objs = struct.unpack('I', f.read(4))[0]
        #print("objs: " + str(objs))
        data = f.read().decode('latin-1')
        
        GMregex = re.compile("cAssetBasicSetObject")
        for iter in GMregex.finditer(data):
            offset = iter.start()
            #print("Offset: " + str(offset))
            f.seek(offset+25)
            
            x = struct.unpack('f', f.read(4))[0]
            y = struct.unpack('f', f.read(4))[0]
            z = struct.unpack('f', f.read(4))[0]
            rx = struct.unpack('f', f.read(4))[0]
            ry = struct.unpack('f', f.read(4))[0]
            rz = struct.unpack('f', f.read(4))[0]
            sx = struct.unpack('f', f.read(4))[0]
            sy = struct.unpack('f', f.read(4))[0]
            sz = struct.unpack('f', f.read(4))[0]
            
            name = GetName(f)
            temp = name
            name = self.FindNearestGMMatch(name)
            if name == -1:
                print("\nError: " + temp)
                print("!!! Unable to find mod3 path, skipping !!!\n")
                continue
            
            loc = [x, y, z]
            rot = [rx, ry, rz]
            scale = [sx, sy, sz]
            
            keyData = {"loc": loc, "scl": scale, "rot": rot}
            
            if name in self.transforms:
                self.transforms[name].append(keyData)
            else:
                self.transforms[name] = [keyData]
            


        
    # Returns an array of all GM paths
    def GenerateGMList(self):
        print("Find all GM mod3s...")
        gms = []
        globCMD = self.chunk + 'Assets\\**\\*gm*.mod3'
        gms = gms + glob.glob(globCMD, recursive = True)
        globCMD = self.chunk + 'vfx\\**\\*gm*.mod3'
        gms = gms + glob.glob(globCMD, recursive = True)
        globCMD = self.chunk + 'stage\\**\\*gm*.mod3'
        gms = gms + glob.glob(globCMD, recursive = True)
        globCMD = self.chunk + 'common\\**\\*gm*.mod3'
        gms = gms + glob.glob(globCMD, recursive = True)
        return gms
        

    # Very hacky but idc lol xD
    def FindNearestGMMatch(self, id):
        #print("Target: " + id)
        for i in self.GMList:
            if id+".mod3" in i:
                print(id + " : " + i)
                return i
        
        #print("Trying trim")
        id = id[:-3]
        for i in self.GMList:
            if id+".mod3" in i:
                print(id + " : " + i)
                return i
        
        #print("Trying GMA parse")
        temp = self.ParseGMA(id)
        if temp != -1:
            print(id + " : " + temp)
            return temp
            

        return -1


    # These are only present for st101 -> st109, 403, 409
    def ParseGMA(self, n):
        stageID = self.stageDir[self.stageDir[:-1].rfind("\\")+1:-1] #lol
        #print("stageID " + str(stageID))
        GMAPath = self.chunk + "Assets\\gm\\" + stageID + "\\" + n + ".gma"
        #print("GMAPath " + GMAPath)
        if not os.path.exists(GMAPath):
            return -1
            
        f = open(GMAPath, 'rb')
        data = f.read().decode('latin-1')
        GMregex = re.compile("Assets")
        gmName = []
        # Find all asset references
        for iter in GMregex.finditer(data):
            offset = iter.start()
            f.seek(offset)
            temp = GetName(f)
            if "\\col\\" not in gmName:
                gmName.append(temp)
        # Mod name will be the shortest path
        return self.chunk + min(gmName, key=len) + ".mod3"
            
         
    


class iprImportOperator(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "custom_import.import_ipr"
    bl_label = "Import ipr stage"
    bl_options = {'REGISTER', 'PRESET', 'UNDO'}

    filename_ext = "*.ipr;*.bkipr;*.sobj"
    filter_glob = StringProperty(default="*.ipr;*.bkipr;*.sobj", options={'HIDDEN'}, maxlen=255)

    include_sobj = BoolProperty(
            name="Include SOBJ with IPR",
            description="Find and load SOBJ assets when loading an .ipr stage",
            default=False,
            )
    
    include_terrains = BoolProperty(
            name="Include terrains with IPR",
            description="Find and load all terrains when loading an .ipr stage",
            default=False,
            )
            
    skip_IPR = BoolProperty(
            name="Skip IPRs",
            description="Only load terrains on IPR load",
            default=False,
            )        

    def execute(self, context):
        fp = self.properties.filepath
        temp = HuntUp(fp, "Assets")
        self.chunk = temp[:temp.rfind("\\")] + "\\"
        print("Using chunk dir: " + self.chunk)
        self.iprName = fp[fp.rfind("\\")+1:]
        self.scn = bpy.context.scene
        
        
        

        
        
        if not self.skip_IPR:
            #### Terrain assets #####
            print("Loading IPR assets")
            modTable = self.DecodeIPR(self.properties.filepath)
            i = 0
            for x in modTable:
                i += 1
                print(str(i) + "/" + str(len(modTable)) + " Importing: " + x + " count: " + str(len(modTable[x])))
                self.ImportModel(x, modTable[x])
            ####
        

        if self.include_sobj:
            ##### sobj assets #####
            print("Loading SOBJ assets")
            stageDir = fp[:fp.rfind("\\")]
            stageDir = stageDir[:stageDir.rfind("\\")]
            stageDir = stageDir[:stageDir.rfind("\\")+1]
            print(stageDir)
            
            sOBJ = SOBJParser(stageDir, self.chunk)
            modTable = sOBJ.transforms
            i = 0
            for x in modTable:
                i += 1
                print(str(i) + "/" + str(len(modTable)) + " Importing: " + x + " count: " + str(len(modTable[x])))
                self.ImportModel(x, modTable[x])
            #####
        
        if self.include_terrains:
            ##### Terrains #####
            print("Loading MOD terrains")
            # Most terrains exist in parent directory mod3
            modPath = fp[:fp.rfind("etc")] + "mod\\*.mod3"
            k = glob.glob(modPath, recursive = True)
            # But some are in the same dir as the .ipr such as title menus, or sdl
            modPath = fp[:fp.rfind("\\")+1] + "**\\*.mod3"
            k += glob.glob(modPath, recursive = True)
            i = 0
            for m in k:
                i += 1
                print(str(i) + "/" + str(len(k)) + " " + m)
                bpy.ops.custom_import.import_mhw_mod3(filepath=m, clear_scene=False, maximize_clipping=False, import_materials=True, import_skeleton='None')
            #####


        
        self.ApplyEmptyParent()
        print("Velkhana best monster")
        return {'FINISHED'}



        


    def ImportModel(self, id, trfs):
        if os.path.exists(id):
            bpy.ops.custom_import.import_mhw_mod3(filepath=id, clear_scene=False, maximize_clipping=False, import_textures=False, import_materials=True, import_skeleton='None')
        else:
            print("File not found, ommiting")

        # Unfortunately we do not get a reference back
        # Find it by name, and reference by last index
        
        # An import sometimes has multiple objs, so, iterate through each one
        objs = [obj for obj in bpy.context.scene.objects if not obj.name.startswith("_")]
        
        for o in objs:
            #print("Parsing: " + str(o))
            if "Armature" in o.name:
                continue
            
            self.ApplyTransforms(o, trfs[0])
            if len(trfs) > 1:
                for i in range(1, len(trfs)):
                    #print("Duplicate " + str(i) + "/" + str(len(trfs)))
                    new_obj = o.copy()
                    #new_obj.data = o.data.copy() #NOOOOOO
                    self.scn.objects.link(new_obj)
                    self.ApplyTransforms(new_obj, trfs[i])
                    
            
    def ApplyTransforms(self, obj, trfs):
        obj.name = "_" + obj.name
        obj.location = trfs["loc"]
        obj.scale = trfs["scl"]

        if len(trfs["rot"]) == 4:
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = trfs["rot"]
            
        if len(trfs["rot"]) == 3:
            obj.rotation_mode = 'XYZ'
            obj.rotation_euler = trfs["rot"]

            obj.rotation_euler[0] = math.radians(trfs["rot"][0])
            obj.rotation_euler[1] = math.radians(trfs["rot"][1])
            obj.rotation_euler[2] = math.radians(trfs["rot"][2])
        

    # Applies everything to an empty parent, which applies a transform fix
    def ApplyEmptyParent(self):
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
        empty = bpy.context.selected_objects[0]
        empty.name = self.iprName
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        empty.rotation_euler[0] = math.radians(90)
        empty.scale[0] = 0.01
        empty.scale[1] = 0.01
        empty.scale[2] = 0.01


    # Given file offset and count, return dict of transforms
    def GetTransforms(self, f, offset, count):
        f.seek(offset)
        modTable = []
        for i in range(0, count):
            DATA = f.read(144)
            temp = []
            for x in range(0, 144, 4):
                temp.append(struct.unpack('f', DATA[x:x+4])[0])

            loc = Vector((float(temp[0]), float(temp[1]), float(temp[2])))
            scale = Vector((float(temp[3]), float(temp[4]), float(temp[5])))
            rot = [temp[9], temp[6], temp[7], temp[8]]

            keyData = {"loc": loc, "scl": scale, "rot": rot}
            modTable.append(keyData)
        return modTable



    

    def DecodeIPR(self, iprPath):
        f = open(iprPath, 'rb')

        f.seek(64)
        P = f.read(8) #idk what this is lol, it's always "P"
        objs = struct.unpack('I', f.read(4))[0]
        print("objs: " + str(objs))

        # Object header stuff starts now
        f.seek(112) # Add +16 for .bkipr
        header = []

        # Parse Header to get object offsets and count
        for i in range(0, objs):
            DATA = f.read(64)
            temp = []
            for x in range(0, 64, 8):
                temp.append(struct.unpack('I', DATA[x:x+4])[0])
            header.append(temp)
            print(temp)
            # 32 byte gap
            if i != objs: f.read(64)

        transforms = {}
        for i in header:
            f.seek(i[0])
            name = GetName(f)
            id = self.chunk + name + ".mod3"
            transforms[id] = self.GetTransforms(f, i[6], i[7])

        return transforms


def menu_func_import(self, context):
    self.layout.operator(iprImportOperator.bl_idname, text="MHW Stage (.ipr)")


def register():
    bpy.utils.register_class(iprImportOperator)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(iprImportOperator)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)