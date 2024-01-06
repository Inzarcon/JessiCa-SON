# JessiCa: Serpents Obstruct None
(Repo private while under construction.)

***JessiCa: Serpents Obstruct None*** is (going to be) a *Qt 6*-powered tileset configurator for *Cataclysm: Dark Days Ahead*. Currently, *JessiCa* is in an early prototyping/alpha stage, but its core GUI wrapper for `compose.py` is functional. Using *Nuitka Python* compiler magic, the *JessiCa* executable is bundled with everything it needs for tileset composing. Most notably, this includes a minimal *Python* runtime, *libvips*, and the tileset tools themselves. No installations or setting environment variables required - just unzip and run `JessiCa.exe`.

## Downloads
Releases: [add]

Source: Clone this repository or download the .zip archive. [add]

Note that bundled application releases target **64-Bit *Windows 10+* only** at this time. However, you can use *Python* to run *JessiCa* directly from source, just like running `python compose.py` as usual. Additionally, you may attempt compiling the executable package for another platform yourself. The following sections explain this in more detail.

## Running with *Python* and (optional) Compiling

The general setup is similar to the one described in the [original TILESET.md](https://github.com/CleverRaven/Cataclysm-DDA/blob/master/doc/TILESET.md#pyvips)  from the Cataclysm-DDA Repository, with additional packages such as the *PySide6 Python* bindings for *Qt 6.* In order to install *Python* itself, you can use the official installer from [python.org](https://www.python.org/downloads/). On *Windows*, make sure to **enable the installer's 'add Python to PATH'** and **install with Pip** options[^1]. Open a command prompt/terminal (*Windows*: Searchbar or `Win` + `R`. Then type "cmd" and hit `Enter`). To install the requirements, type or copy/paste the following command into the console:
```
C:\Users\[Your Username]>pip install pyside6 pyvips typing_extensions tqdm icecream
```
Alternatively, if you already downloaded the *JessiCa* sources, you can point *Pip* to its requirements file:
```
C:\[Where you put JessiCa Sources]>pip install -r requirements.txt
```
[ToDo: Automatic split into basic requirements and additional dev-tools] 

Finally, you can now run *JessiCa* :
```
C:\[Where you put JessiCa Sources]> python .\main.py
```

[ToDo: Just do Python commands in .bat like tilesets repo?] 

[^1]:This is fine for most users. If you need multiple non-conflicting *Python* installations, package managers like [*conda*](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html) or the much faster [*mamba*](https://github.com/mamba-org/mamba) are recommended instead.
