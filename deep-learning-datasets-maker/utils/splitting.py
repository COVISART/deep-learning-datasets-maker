try:
    from osgeo import gdal
except:
    import gdal

import os.path as osp
import math

from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsProcessingFeedback,
    QgsMessageLog,
    Qgis,
    QgsTask,
    QgsApplication
)
MESSAGE_CATEGORY = 'COVISART'
def scale_to_percentage(value, max_value):
    if max_value == 0:
        raise ValueError("max_value cannot be zero.")
    if value < 0 or value > max_value:
        raise ValueError("value must be between 0 and max_value.")
    return (value / max_value) * 100
# Start Splitting 
def splitting(
        fn_ras, 
        cdpath, 
        frmt_ext, 
        imgfrmat, 
        scaleoptions, 
        needed_out_x, 
        needed_out_y, 
        file_name):
    feedback = QgsProcessingFeedback()
    ds = gdal.Open(fn_ras)
    if not ds:
        feedback.pushInfo("Error: Can not open file:" + fn_ras)
        return
    gt = ds.GetGeoTransform()
    if gt:
        feedback.pushInfo("Origin = ({}, {})".format(gt[0], gt[3]))
        feedback.pushInfo("Pixel Size = ({}, {})".format(gt[1], gt[5]))
    else :
        feedback.pushInfo('GetGeoTransform error ')
    # get coordinates of upper left corner
    xmin = gt[0]
    ymax = gt[3]
    resx = gt[1]
    res_y = gt[5]
    resy = abs(res_y)

    # round up to nearst int
    xnotround = ds.RasterXSize / needed_out_x
    xround = math.ceil(xnotround)
    ynotround = ds.RasterYSize / needed_out_y
    yround = math.ceil(ynotround)

    # pixel to meter - 512×10×0.18
    pixtomX = needed_out_x * xround * resx
    pixtomy = needed_out_y * yround * resy
    # size of a single tile
    xsize = pixtomX / xround
    ysize = pixtomy / yround
    # create lists of x and y coordinates
    xsteps = [xmin + xsize * i for i in range(xround + 1)]
    ysteps = [ymax - ysize * i for i in range(yround + 1)]

    
    QgsMessageLog.logMessage('xround {}'.format(xround),
                                MESSAGE_CATEGORY, Qgis.Info)
    QgsMessageLog.logMessage('yround {}'.format(yround),
                                MESSAGE_CATEGORY, Qgis.Info)
    # loop over min and max x and y coordinates
    for i in range(xround):
        for j in range(yround):
            xmin = xsteps[i]
            xmax = xsteps[i + 1]
            ymax = ysteps[j]
            ymin = ysteps[j + 1]

            # use gdal warp
            # gdal.WarpOptions(outputType=gdal.gdalconst.GDT_Byte)
            # gdal.Warp("ds"+str(i)+str(j)+".tif", ds,
            # outputBounds = (xmin, ymin, xmax, ymax), dstNodata = -9999)
            
            # or gdal translate to subset the input raster
            savePath = osp.join(cdpath,  \
                                    (str(file_name) + "-" + str(j) + "-" + str(i) + "." + frmt_ext))
            feedback.pushInfo("gdalSavePath : " + savePath)
            feedback.pushInfo("projWin : " + str((abs(xmin), abs(ymax), abs(xmax), abs(ymin))))
            feedback.pushInfo("xRes : " + str(resx))
            feedback.pushInfo("yRes : " + str(resy))
            feedback.pushInfo("outputType : " + str(gdal.gdalconst.GDT_Byte))
            feedback.pushInfo("format : " + imgfrmat)
            kwargs = {
                'projWin': (abs(xmin), abs(ymax), abs(xmax), abs(ymin)),
                'xRes': resx,
                'yRes': resy,
                'outputType': gdal.gdalconst.GDT_Byte,
                'format': imgfrmat
            }
            gdal.Translate(savePath, 
                        ds, 
                        **kwargs)
            QgsApplication.processEvents()  # UI'yi güncellemek için (isteğe bağlı)
        if feedback.isCanceled():
            # Eğer görev iptal edilirse işlemi durdurun
            return False
        feedback.setProgress(scale_to_percentage(i, xround))
# Create a few tasks

# close the open dataset!!!
ds = None