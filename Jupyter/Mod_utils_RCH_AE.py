import numpy as np
import pandas as pd
import os
import shapefile as shp
import flopy
from flopy.utils.gridintersect import GridIntersect
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiLineString, MultiPoint, MultiPolygon

def zonas_pozas(sim,filename,zone_array,nfield):
    ix = GridIntersect(sim.modelgrid, method="vertex", rtree=True)
    shp_rdir_obj = shp.Reader(filename)
    shapeRecs = shp_rdir_obj.shapeRecords()
    nrow = zone_array.shape[1]
    ncol = zone_array.shape[2]
    
    areas_arr = np.zeros((len(shapeRecs),nrow,ncol), dtype=float) #arreglo que contendrá que cantidad de cada zona de
    a=int(nfield)                                                              #recarga (en área) hay en cada celda

    zonas=np.zeros((1,areas_arr.shape[0]), dtype=float) 
    
    for ishape in range(len(shapeRecs)):
        shape = shapeRecs[ishape].shape
        rec_zone = shapeRecs[ishape].record[:a][a-1] ######## verificar que se puede leer la zona --> si funciona pero lee el 1° campo
        zonas[0,ishape] = int(rec_zone)  #tenemos la zona de cada poligono. verificar si se lee la zona --> si funciona
        polyg_points = shape.points #pasar a puntos
        p = Polygon(shell=polyg_points) #volver a polígonos
        result = ix.intersect(p) #intersectar 
        cellids = result['cellids']
        areas = result['areas']
        for icell in range(len(cellids)):
            areas_arr[ishape,cellids[icell][0],cellids[icell][1]]=areas[icell]

    areas=np.zeros((1,areas_arr.shape[0]), dtype=float) #arreglo q contendrá la cantidad de area de las zonas de recarga 
                                                        #para cada celda 
    for irow in range(nrow):
        for icol in range(ncol):
            for ipol in range(areas_arr.shape[0]):
                areas[0,ipol] = areas_arr[ipol,irow,icol]
            zone_array[0,irow,icol]=zonas[0,np.argmax(areas,axis=1)]   ###verificar si funciona --> si funciona
            #zona_array es un arreglo que para cada celda le asigna una zona. ojo q el numerativo del array empieza en 0

    return zone_array, areas_arr

def recarga_mensual(filename1,filename2):
    # Calculamos la recarga mensual, la pasamos a m3/d dividiendo por 86.4 y dividimos tb por el area total y días del mes
    # filename1 es un csv con la fecha y la infiltración diaria en l/s
    # filename2 es un csv con el área de cada zona
    df = pd.DataFrame(data=filename1)

    df.Fecha = pd.to_datetime(df.Fecha, format='%d/%m/%Y')
    df.set_index('Fecha', inplace=True)
    
    df_mes = df.resample('MS').sum()  #calculo de recarga mensual
    
    #ahora las conversiones
    #primero obtener los dias de cada mes
    df_mes_R = df_mes.reset_index() 
    df_fecha = df_mes_R.iloc[0:,0]
    df_fecha = df_fecha.apply(lambda t: pd.Period(t, freq='S').days_in_month).tolist() #se pasa a lista
    inv_fecha = [1/i for i in df_fecha] #se calcula el inverso para futuros calculos
    
    #segundo obtener el área de cada zona
    areas_rec = filename2['Area_m2'].tolist()
    a = [i * (1/86.4) for i in areas_rec] #se multiplica por un factor para despues poder pasar la recarga de l/s a m3/d
    
    #calculos finales
    t = df_mes/a #se divide por el area total de la zona
    tasa = t.mul(inv_fecha, axis=0) #se multiplica el anterior el inverso de la cantidad de días del mes
    
    return tasa
