# sector-light-illumination
![Map of the archipelago sea with amount of illuminance caused by the sector lights](https://user-images.githubusercontent.com/107625176/211839658-ca4fd064-8293-4067-bfa1-2f2a42dd6320.png)
Visualised example output of the tool from the archipelago sea

## Background
Light pollution is important and underreasearched problem. I wanted to create a tool for finding the most and least illuminated areas in the Finnish coast. 
## Usage
Currently the code is  a PyQGIS script, which should be run from inside QGIS. Getting it to work requires:
- Downloading DEMs from the target area, preferably so that it consists of multiple tiffs with size of 5–30 km (e.g. DEMs of the National Land Survey of Finland)
- Downloading and preprocessing the sector light geodata. It must be a geopackage and it must include attributes on the height (meters from water), brightness (candelas), optical range (meters), light sector start angle, end angle, central angle and total width of the sector light. 
- editing the code. At least paths need to be changed. Only linux has been tested, so running the script on other systems may need more tinkering or may just not work.

### In summary, if you want to actually run the code you should contact me. The script is nowhere near completed piece of software, and is known to contain bugs that prevent the processing of small portion of the features.
