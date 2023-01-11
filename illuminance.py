from time import perf_counter
from statistics import mean
from os.path import exists
import shutil
import os, re, os.path
import subprocess
import glob

def convert_sec(seconds):
    """ Prints pretty seconds
    """
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
     
    return "%d:%02d:%02d" % (hour, minutes, seconds)

def collect_garbage(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            os.remove(os.path.join(root, file))

def cone_bounds(light_point):
    """Calculates and returns the bounding box of the light cone 
    of the given sector light
    """
    # Calculating the sector area
    wedge = processing.run("native:wedgebuffers",
    {'INPUT':light_point,
    'AZIMUTH':QgsProperty.fromExpression('"keskikulma"'),
    'WIDTH':QgsProperty.fromExpression('"kulmaleveys"'),
    'OUTER_RADIUS':QgsProperty.fromExpression('"opt_kanto_m"'),
    'INNER_RADIUS':0,'OUTPUT':'TEMPORARY_OUTPUT'})
    
    # Adds a small buffer(the size of the resolution) to ensure that the light source is within the raster
    buffer = processing.run("native:buffer", {
    'INPUT':wedge['OUTPUT'],'DISTANCE':10,'SEGMENTS':5,
    'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
    'DISSOLVE':False,'OUTPUT':'TEMPORARY_OUTPUT'})
    
    # Calculating the bounding box of the sector
    bbox = processing.run("native:polygonfromlayerextent",
    {'INPUT': buffer['OUTPUT'],'ROUND_TO':25,'OUTPUT':'TEMPORARY_OUTPUT'})
    return bbox['OUTPUT']

def gdal_transform_clip_parser(bbox, vrt_path, out_path):
    """ parses and returns shell command to run gdal_transform
    so that it creates a bounding box sized clip from a given large virtual raster
    and saves the resulting clipped tif to a given location
    """
    feats = bbox.getFeatures() 
    # There is only one feature in the bbox layer, but iteration is a convenient way to get it
    for feat in feats:
        # geometry of the bbox
        bbox_geom = feat.geometry().boundingBox()
        # upper left x, lower right y, lower right x, upper left y coordinates of the bounding box
        ulx, lry, lrx, uly = bbox_geom.toRectF().getCoords()
        command = f"gdal_translate -projwin {ulx} {uly} {lrx} {lry} {vrt_path} {out_path}"
    return command

def create_vrt(vrt_path, target_directory):
    """ Creates a vrt from all tif files in the directory of the given path
    and it's subdirectories. vrt_name should include ".vrt" at the end
    """
    root_directory, vrt_name = os.path.split(vrt_path)
    data_directory = os.path.join(root_directory, target_directory, '')
    data_files = [file for file in glob.glob(data_directory + "**/*.tif", recursive=True)]
    
    # Creating the vrt
    processing.run("gdal:buildvirtualraster",
    {'INPUT':data_files,'RESOLUTION':0,'SEPARATE':False,
    'PROJ_DIFFERENCE':False,'ADD_ALPHA':False,'ASSIGN_CRS':None,
    'RESAMPLING':0,'SRC_NODATA':'','EXTRA':'','OUTPUT':vrt_path})
    
def create_zero_vrt(dem_path, vrt_path):
    """ Creates a copy of the given files in dem_path to data directory in the
    same directory as the given vrt path and creates a vrt with all zero values.
    """
    zero_dir, fname = os.path.split(vrt_path)
    data_dir = os.path.join(zero_dir, "zeroes", '')
    if not exists(data_dir):
        os.makedirs(data_dir)

    demdir, dem_vrt_name = os.path.split(dem_path)
    # Modifies the path by adding a / or \ to the path, depending on os
    demdir = os.path.join(demdir, '')
    dem_paths = [file for file in glob.glob(demdir + "**/*.tif", recursive=True)]
    
    
    
    """Checks for wether there are as many tif files already in datadir
    as in dem_paths, if yes, files are not moved or reclassified
    """
    data_paths = [file for file in glob.glob(zero_dir + "**/*.tif", recursive=True)]
    if not len(data_paths) == len(dem_paths):
        """Because the paths don't contain equal amount of tiffs, all the tiffs
        in the data directory are deleted and then all the tiffs in the dem
        directory are copied to the data directory with all values set to 0
        """
        for data_path in data_paths:
            os.remove(data_path)
        
        # progress counter for printing stats
        counter = 0
        
        print("Copying and reclassifying dem to create all zero rasters")
        for dem in dem_paths:
            dem_dir, dem_name = os.path.split(dem)
            out_path = os.path.join(data_dir, dem_name)
        
            # Reclassifying the dem so that all the values get set to 0
            processing.run("native:reclassifybytable", {
            'INPUT_RASTER':dem,'RASTER_BAND':1,'TABLE':['-100','2000','0'],
            'NO_DATA':-9999,'RANGE_BOUNDARIES':0,'NODATA_FOR_MISSING':False,
            'DATA_TYPE':5,'OUTPUT':out_path})
        
            counter += 1
            if counter % 100 == 0:
                print(f"{counter} / {len(dem_paths)} reclassified")
    
    else:
        print("Files already in place, skipping copying and reclassifying")
    
    print("Creating vrt from the tiffs")
    create_vrt(vrt_path, data_dir)
    

"""File location of the initial sector light file 
(a geopackacge with 1 point per layer)
TODO: change the code to take in multiple features in a layer, because current
implementation is slow to set up and not using geopackage as intented
"""
filepath = "/home/iiro/980/GIS980/light_cones/lights/loistot_alkuprosessointi.gpkg|layername=loistot_alkuprosessointi"

""" File location for the vrt dem. if it does not yet exist, it is created from
the tif_files in the same folder and folders below it. Vrt is used because it is 
efficient format when processing small subareas from large dataset
"""
vrt_dem_path = '/home/iiro/980/GIS980/korkeusmalli_10_m/korkeusmalli_10_m.vrt'
if not exists(vrt_dem_path):
    demdir, fname = os.path.split(vrt_dem_path)
    create_vrt(demdir, "dem10m")
    print("Dem vrt created")
    
""" File location for an all zero vrt . if it does not yet exist, it is created 
from the tif_files in the folders containing the dem. This includes copying all 
the tif files in the dem folder and setting their value to zero
Vrt is used because it is efficient format when processing small subareas from large dataset
"""
# TODO rename empty variables to variation of zero
empty_vrt_path = '/home/iiro/980/GIS980/light_cones/zeroes.vrt'
if not exists(empty_vrt_path):
    create_zero_vrt(vrt_dem_path, empty_vrt_path)

""" Filepath of the end result, also a vrt. The result vrt is created by copying 
all the tifs with zeroes as value and then adding illuminance caused by each light 
to the relevant tiffs. A vrt is created pointing to all the resulting tiffs.
"""

print("Creating result vrt")
result_vrt_path = '/home/iiro/980/GIS980/light_cones/results.vrt'
result_directory, result_name = os.path.split(result_vrt_path)
# adding "" at the end results in / or \ in the end depending on th os
result_directory = os.path.join(result_directory, "results", "")
print(f"result directory:{result_directory}")
if not exists(result_directory):
    os.makedirs(result_directory)

# If there are already tiffs in the result directory, they are removed
old_result_files = [file for file in glob.glob(result_directory + "**/*.tif", recursive=True)]
print(f"{len(old_result_files)} files overwritten from {result_directory}")
for old_result in old_result_files:
    os.remove(old_result)
# zero rasters are copied to the result directory
zero_dir, zero_vrt_name = os.path.split(empty_vrt_path)
zero_dir = os.path.join(zero_dir, "")
zero_files = [file for file in glob.glob(zero_dir + "**/*.tif", recursive=True)]
for zero_file in zero_files:
    zero_dir, fname = os.path.split(zero_file)
    result_path = os.path.join(result_directory, fname)
    # Makes a copy of the zero rasters, to which all illuminance values are added later
    shutil.copy(zero_file, result_path)


#Creating a vrt
if not exists(result_vrt_path):
    create_vrt(result_vrt_path, result_directory)

# Creates temporary directories for use
point_dir = "/home/iiro/980/GIS980/tmp/point/"
dem_dir = "/home/iiro/980/GIS980/tmp/dem/"
zeroes_dir = "/home/iiro/980/GIS980/tmp/zeroes/"
viewshed_dir = "/home/iiro/980/GIS980/tmp/viewshed/"
rasterization_dir = "/home/iiro/980/GIS980/tmp/rasterization/"
raster_buff_dir = "/home/iiro/980/GIS980/tmp/raster_buff/"
proximity_dir = "/home/iiro/980/GIS980/tmp/proximity/"
raster_calc_dir = "/home/iiro/980/GIS980/tmp/raster_calc/"
merge_dir = "/home/iiro/980/GIS980/tmp/merged/"
out_dir = "/home/iiro/980/GIS980/tmp/out/"
grid_cell_dir = "/home/iiro/980/GIS980/tmp/grid_cell/"
# List of temporary directories
temp_directories = [
point_dir, dem_dir, zeroes_dir, viewshed_dir, 
rasterization_dir, raster_buff_dir, proximity_dir,
raster_calc_dir, merge_dir, out_dir,
grid_cell_dir]

# Creating the temporary directories
for temp_directory in temp_directories:
    if not os.path.isdir(temp_directory):
        os.mkdir(temp_directory)

#TODO change
# Reading the points from geopackage
light_points_file = QgsVectorLayer(filepath, "lights", "ogr")
light_points = light_points_file.getFeatures()

# Opening the shapefile containing all the map sheets(the footprint of the tiffs)
map_sheets = QgsVectorLayer(
"/home/iiro/980/GIS980/korkeusmalli_10_m/dem10m/2019/dem10m.shp",
"map_sheets", "ogr")
    
print("Starting processing")
# Initializing counter for progress
processed_lights = 0
# Start time counter for the whole loop
start_time = perf_counter()

# Initialize lists of performance metrics, one loop == one entry
pre_viewshed_time = []
viewshed_time = []
after_viewshed_time = []
merging_time = []
summation_time = []
sheetifying_time = []
loop_time = []
for light_point in light_points:
    loop_start = perf_counter()
    
    # Converts the processed feature to vector layer and saves it to temp file
    feature_id = light_point['fid']
    point_path = point_dir + str(feature_id) + ".gpkg"
    selection_expression = f'"fid"=\'{feature_id}\''
    light_points_file.selectByExpression(selection_expression)
    selection = map_sheets.selectedFeatures()
        
    # Save the selected feature to temporary location as geopackage
    QgsVectorFileWriter.writeAsVectorFormat(
    light_points_file, point_path, "utf-8", 
    light_points_file.crs(), "GPKG", 1)
    
    # Opening the new layer
    light_point = QgsVectorLayer(point_path, "light_point", "ogr")
    
    #for testing purposes
    #QgsProject.instance().addMapLayer(light_point)
    
    #TODO convert to os.path.join?
    # Creating filenames for the temporary outputs
    dempath = dem_dir + str(feature_id) + ".tif"
    zeroes_path = zeroes_dir + str(feature_id) + ".tif"
    viewshed_path = viewshed_dir + str(feature_id) + ".tif"
    rasterization_path = rasterization_dir + str(feature_id) + ".tif"
    raster_buff_path = raster_buff_dir + str(feature_id) + ".tif"
    proximity_path = proximity_dir + str(feature_id) + ".tif"
    raster_calc_path = raster_calc_dir + str(feature_id) + ".tif"
    merge_path = merge_dir + str(feature_id) + ".tif"
    out_path = out_dir + str(feature_id) + ".tif"
    """ Fetching useful values from the base layer,
    There should only be one feature in layer
    """
    for feature in light_point.getFeatures():
        opt_distance = feature["opt_kanto_m"]
        luminosity = feature["teho_valov"]
        light_id = feature["jnr"]
        print(f"processing light jnr: {light_id}")
    
    """ Gets bounding box of the light cone buffered slightly to ensure
    the light point stays inside the bbox
    """
    bbox = cone_bounds(light_point)
    """ Parsing shell commands for clipping required tiffs from the bbox
    area of the vrt
    """
    dem_clip_command = gdal_transform_clip_parser(bbox, vrt_dem_path, dempath)
    zeroes_clip_command = gdal_transform_clip_parser(bbox, empty_vrt_path, zeroes_path)
    out_clip_command = gdal_transform_clip_parser(bbox, result_vrt_path, out_path)
    
    
    # Actual clipping and saving of the rasters
    subprocess.call(dem_clip_command, shell=True)
    subprocess.call(zeroes_clip_command, shell=True)
    subprocess.call(out_clip_command, shell=True)
    

    """ Creates viewpoint from the point, which is just a regular point but
    with specially formatted fields. This is required for viewshed
    """
    viewpoint = processing.run("visibility:createviewpoints",
    {'OBSERVER_POINTS': light_point,
    'DEM':dempath,
    'OBSERVER_ID':'','RADIUS':5000,'RADIUS_FIELD':'opt_kanto_m',
    'OBS_HEIGHT':1.6,'OBS_HEIGHT_FIELD':'kork_ved',
    'TARGET_HEIGHT':0,'TARGET_HEIGHT_FIELD':'','RADIUS_IN_FIELD':'',
    'AZIM_1_FIELD':'alkukulma_loistosta','AZIM_2_FIELD':'loppukulma_loistosta',
    'ANGLE_UP_FIELD':'','ANGLE_DOWN_FIELD':'','OUTPUT':'TEMPORARY_OUTPUT'})
    before_viewshed = perf_counter()
    
    # Calculates viewshed for the current sector light
    processing.run("visibility:viewshed", 
    {'ANALYSIS_TYPE':0,
    'OBSERVER_POINTS':viewpoint['OUTPUT'],
    'DEM':dempath,
    'USE_CURVATURE':True,'REFRACTION':0.13,'OPERATOR':0,
    'OUTPUT':viewshed_path})
    
    after_viewshed = perf_counter()
    
    # Copies the raster at zeroes path to raster buff directory 
    #TODO name is based on legacy, should be changed
    shutil.copy(zeroes_path, raster_buff_path)
    
    # Adds the sector light to the raster in raster_buff path as cell with value 1
    processing.run("gdal:rasterize_over",
    {'INPUT':light_point,'INPUT_RASTER':raster_buff_path,'FIELD':'vakio',
    'ADD':True,'EXTRA':''})
    
    # Calculates the raster distance (proximity) from the sector light
    processing.run("gdal:proximity", {
    'INPUT': raster_buff_path,'BAND':1,'VALUES':'1',
    'UNITS':1,'MAX_DISTANCE':0,'REPLACE':0,
    'NODATA':0,'OPTIONS':'','EXTRA':'',
    'DATA_TYPE':5,'OUTPUT':proximity_path})
    
    #TODO make changes to inputs and outputs
    # Fetching values required by raster calculator in format it needs
    entries = []
    
    viewshed_raster = QgsRasterLayer(viewshed_path)
    viewshed = QgsRasterCalculatorEntry()
    viewshed.raster = viewshed_raster
    viewshed.ref = 'view@1'
    entries.append(viewshed)
    
    
    proximity_raster = QgsRasterLayer(proximity_path)
    proximity = QgsRasterCalculatorEntry()
    proximity.raster = proximity_raster
    proximity.ref = 'prox@1'
    entries.append(proximity)
    
    """ Takes the proximity raster and calculates an inverse sqaure of it.
    This calculation tells how much weaker the light is at a certain distance. 
    After that the inverse squared distance is multiplied by 1
    at all the places the light from the sector light can reach (viewshed)
    and by 0 on all other places. Finally the value is multiplied
    by the luminosity of the sector light to get illuminance (in luxes)
    caused by the sector light at the particular location
    """
    # Setting up the calculator
    calc = QgsRasterCalculator(
    f'(1 / (prox@1) ^ 2) * (view@1 = 1) * {luminosity}',
    raster_calc_path, 'GTiff', viewshed_raster.extent(),
    viewshed_raster.width(), viewshed_raster.height(), entries) 
    # Actual processing
    calc.processCalculation()
    
    after_lux = perf_counter()
    
    # Todo this needs at least different input
    """The raster calculator result is merged with the all-zero raster.
    This is done in order to avoid issues with nodata and differing 
    viewshed extents between points
    """
    processing.run("gdal:merge",
    {'INPUT':[zeroes_path,raster_calc_path],'PCT':False,
    'SEPARATE':False,'NODATA_INPUT':None,'NODATA_OUTPUT':-1,
    'OPTIONS':'','EXTRA':'','DATA_TYPE':5,
    'OUTPUT': merge_path})
    
    after_merge = perf_counter()
    
    # TODO change input to suitable and output to some temporary location
    # The result is summed to the output file using raster calculator
    entries = []
    
    merged_raster = QgsRasterLayer(merge_path)
    merged = QgsRasterCalculatorEntry()
    merged.raster = merged_raster
    merged.ref = 'merged@1'
    entries.append(merged)
    
    out_raster = QgsRasterLayer(out_path)
    out = QgsRasterCalculatorEntry()
    out.raster = out_raster
    out.ref = 'out@1'
    entries.append(out)
    
    # Setting up the calculator
    calc = QgsRasterCalculator(
    'out@1 + merged@1', out_path, 'GTiff', out_raster.extent(),
    out_raster.width(), out_raster.height(), entries) 
    # Actual processing
    calc.processCalculation()
    
    """
    The output of the raster calculator is sliced into tiffs that
    correspond exactly to the bounds of the used tiffs. Then each old corresponding
    tiff is replaced with new tiff.
    """
    raster_calculator_time = perf_counter()
    
    # Finding wich map sheets overlap with the result
    sheet_intersection = processing.run("native:intersection", {
    'INPUT':map_sheets,'OVERLAY':bbox,'INPUT_FIELDS':['label','data_id'],'OVERLAY_FIELDS':[],
    'OVERLAY_FIELDS_PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})
    # Getting the intersecting features of the map sheets
    sheet_intersection = sheet_intersection['OUTPUT']
    sheet_features = sheet_intersection.getFeatures()
    
    for sheet in sheet_features:
        sheet_label = sheet['label']
        grid_cell_path = os.path.join(grid_cell_dir, sheet_label + ".shp")
        clip_path = os.path.join(out_dir, sheet_label + ".tif")
        diff_clip_path = os.path.join(out_dir, sheet_label + "diff.tif")
        final_path = os.path.join(result_directory, sheet_label + ".tif")
        
        # Selects the feature (map sheet) with correct label
        selection_expression = f'"label"=\'{sheet_label}\''
        map_sheets.selectByExpression(selection_expression)
        selection = map_sheets.selectedFeatures()
        
        # Save the selected feature to temporary location
        QgsVectorFileWriter.writeAsVectorFormat(
        map_sheets, grid_cell_path, "utf-8", 
        map_sheets.crs(), "ESRI Shapefile", 1)
        
        
        """ Clipping the output raster with the map sheet
        """
        processing.run("gdal:cliprasterbymasklayer", {
        'INPUT':out_path,
        'MASK':grid_cell_path,'SOURCE_CRS':QgsCoordinateReferenceSystem('EPSG:3067'),
        'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:3067'),
        'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,
        'CROP_TO_CUTLINE':False,'KEEP_RESOLUTION':True,'SET_RESOLUTION':False,
        'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':True,
        'OPTIONS':'','DATA_TYPE':0,'EXTRA':'',
        'OUTPUT':clip_path})
        
        """ The area of the tiff to be overwritten that does not overlap with the result
        is fetched and combined with the result
        """
        difference = processing.run("native:difference", {
        'INPUT':grid_cell_path,
        'OVERLAY':bbox,
        'OUTPUT':'TEMPORARY_OUTPUT','GRID_SIZE':None})
        difference = difference['OUTPUT']
        
        # Fetches the non overlapping area from the same tiff
        processing.run("gdal:cliprasterbymasklayer", {
        'INPUT':final_path,
        'MASK':difference,'SOURCE_CRS':QgsCoordinateReferenceSystem('EPSG:3067'),
        'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:3067'),
        'TARGET_EXTENT':None,'NODATA':None,'ALPHA_BAND':False,
        'CROP_TO_CUTLINE':False,'KEEP_RESOLUTION':True,'SET_RESOLUTION':False,
        'X_RESOLUTION':None,'Y_RESOLUTION':None,'MULTITHREADING':True,
        'OPTIONS':'','DATA_TYPE':0,'EXTRA':'',
        'OUTPUT':diff_clip_path})
        
        """ This check is necessary, because there are cases where the entire
        map sheet is in the area of the clip, and diff_clip is empty and thus
        not created. In these cases, the clip result can just be copied to its'
        place
        """
        if exists(diff_clip_path):
            """ The area of the tiff to be overwritten that does not overlap with the result
            is merged with the result. Output overwrites the old file in
            the results folder.
            """
            processing.run("gdal:merge", {
            'INPUT':[clip_path,
            diff_clip_path],
            'PCT':False,'SEPARATE':False,'NODATA_INPUT':None,
            'NODATA_OUTPUT':None,'OPTIONS':'','EXTRA':'','DATA_TYPE':5,'OUTPUT':final_path})
        else:
            shutil.copy(clip_path, final_path)
        
    end_time = perf_counter()
    
    #Empties the tempfile folders so that they don't become too large
    for temp_directory in temp_directories:
        collect_garbage(temp_directory)
    
    
    # Prints the progress 
    processed_lights += 1
    used_time = round((end_time - start_time), 1)
    print(f"{processed_lights} / {6533} processed in {convert_sec(used_time)}")
    print(f"Estimated time remaining:\n\
{convert_sec((used_time / processed_lights) * 6533 - processed_lights)}")
    
    pre_viewshed_time.append(before_viewshed - loop_start)
    viewshed_time.append(after_viewshed - before_viewshed)
    after_viewshed_time.append(after_lux - after_viewshed)
    merging_time.append(after_merge - after_lux)
    summation_time.append(raster_calculator_time - after_merge)
    sheetifying_time.append(end_time - raster_calculator_time)
    loop_time.append(end_time - loop_start)
    
    
    #if processed_lights == 50:
        #break
    

# rebuilding the result vrt so that it shows correct min and max etc.
print("Rebuilding " + result_vrt_path)
create_vrt(result_vrt_path, result_directory)

print("------------------\n\
     Finished!\n\
------------------")
print(f"Mean time used before viewshed: {round(mean(pre_viewshed_time), 2)}")
print(f"Mean time used for viewshed: {round(mean(viewshed_time), 2)}")
print(f"Mean time used between viewshed and merging: {round(mean(after_viewshed_time), 2)}")
print(f"Mean time used for merge: {round(mean(merging_time), 2)}")
print(f"Mean time used for summation: {round(mean(summation_time), 2)}")
print(f"Mean time used for sheetifying: {round(mean(sheetifying_time), 2)}")
print(f"Mean time used for a loop: {round(mean(loop_time), 2)}")