# MHW Stage Loader

Blender addon to import MHW stage files

## Requirements

- [Blender 2.79b](https://download.blender.org/release/Blender2.79/)
- [MOD3 Importer addon](https://github.com/AsteriskAmpersand/Mod3-MHW-Importer)
- [Unpacked](https://github.com/JodoZT/MHWNoChunk) MHW chunk files, with at least directories: `stage/`, `Assets/`, `vfx/`

## Installation

Download this repo as zip, install in Blender via User Preferences -> Addons -> Install from File

## Usage

1. Choose an `.ipr` or `.bkipr` file via File -> Import -> MHW Stage

## Notes
- View stage IDs at the [Modding wiki here.](https://github.com/Ezekial711/MonsterHunterWorldModding/wiki/Stage-IDs)
- Reveal the console window to see import progress, it can take several minutes.
- To determine the file ID for individual zones from large stages (like st101->st109), load the stages `bkipr` with IPR/SOBJ disabled, this will quickly load a bare stage where you can find the ID from the terrains name.
- Loading an IPR stage will search for all related SOBJ references for that stage, even if it's outside the zone, check **Bound SOBJs** to limit imports within that zone, useful for the big maps.
- Disable SOBJ imports when layering multiple stages.
- The result is parented to an Empty with a transform fix, recommend to disable relationship lines as it gets quite messy.
- Use Shift+F (or tilde for 2.8+) for first person camera controls.
- Not perfect, will miss some assets.
- `bkipr` imports are **very slow!** 
- For research, and personal use only, all output with this addon is copyrighted. 
