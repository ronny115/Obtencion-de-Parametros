import sys
from arcpy.sa import *
import arcpy
import time
import numpy
from datetime import timedelta

def inputs(nombreTer,listaNombres,rasters,rasterPath,contador,archivoTm):
        
        tm = open(archivoTm)
        linea = tm.readline()
        while linea != "":
                nombres = linea.split()
                if nombreTer in nombres:
                        contador = 0
                        for nombresRaster in nombres:
                                exec("Var{0} = nombres[{0}]").format(contador)
                                if contador > 2:
                                        exec("Var{0} = rasterPath + nombres[{0}]").format(contador)
                                contador = contador + 1
                        for ras in range(3 , contador):
                                exec("rasters += Var{0}").format(ras)
                        break
                else:        
                        lista = nombres[0]
                        listaNombres.append(lista)
                        linea = tm.readline()
                        
        if nombreTer not in nombres:
                sys.exit("Nombre del termino municipal incorrecto")
                
        tm.close()
        return Var0,Var1,Var2,rasters
      
def areaSombra(out_name,Var1,Var2,rasterTemp,x,shapeFile):

        print("Calculando area sombreada\n")

        arcpy.CreateTable_management("in_memory", out_name, "", "")
        arcpy.AddField_management(out_name, "Identificador", "DOUBLE", "15", "2", "","", "NULLABLE")
        arcpy.AddField_management(out_name, "Area_Sombreada", "DOUBLE", "15", "2", "","", "NULLABLE")
        arcpy.AddField_management(out_name, "PercentArea", "DOUBLE", "15", "2", "","", "NULLABLE")
        
        for fid in xrange(int(Var1), int(Var2)+1):
                arcpy.MakeFeatureLayer_management(shapeFile, "layer{0}".format(fid), "FID ={0}".format(fid))
                arcpy.Clip_management(rasterTemp,"#","eR{0}".format(fid),"layer{0}".format(fid),"0","ClippingGeometry")

                try:
                        outUnsupervised = IsoClusterUnsupervisedClassification("eR{0}".format(fid), "2", "3")
                        outUnsupervised.save("iC{0}".format(fid))
                except:        
                        print("Error en parcela {0}".format(fid))
                        continue
                
                arcpy.AddField_management("iC{0}".format(fid), "Area_Sombreada", "DOUBLE", "15", "2", "","", "NULLABLE")
                arcpy.AddField_management("iC{0}".format(fid), "Identificador", "DOUBLE", "15", "2", "","", "NULLABLE")
                arcpy.AddField_management("iC{0}".format(fid), "PercentArea", "DOUBLE", "15", "2", "","", "NULLABLE")
                
                with arcpy.da.UpdateCursor("iC{0}".format(fid), ["Identificador"]) as rows:
                        for row in rows:
                                row[0] = fid
                                rows.updateRow(row)
                        
                with arcpy.da.SearchCursor("iC{0}".format(fid),"Count") as rows:
                        for row in rows:
                                x += row[0]

                with arcpy.da.UpdateCursor("iC{0}".format(fid),["Area_Sombreada","PercentArea","Count"]) as rows:
                        for row in rows:
                                row[0] = row[2] * 0.25
                                row[1] = (row[2] / x)*100
                                rows.updateRow(row)
                x = 0
                with arcpy.da.SearchCursor("iC{0}".format(fid),"*","Value = 1") as rows:
                        for row in rows:
                                areaSombreada = row[3]
                                identificador = row[4]
                                percentArea = row[5]
                        
                with arcpy.da.InsertCursor(out_name,["Identificador","Area_Sombreada","PercentArea"]) as cursor:
                        cursor.insertRow((identificador,areaSombreada,percentArea))

                arcpy.Delete_management("iC{0}".format(fid))
                arcpy.Delete_management("eR{0}".format(fid))
                arcpy.Delete_management("layer{0}".format(fid))
                
        arcpy.Delete_management(rasterTemp)

def coeficienteCultivo(out_name,gdbPath,fieldName,Var0,tableFile):

        print("Calculando coeficiente de cultivo\n")

        for meses in xrange(0,13):
		arcpy.AddField_management(out_name, fieldName[int(meses)], "DOUBLE", "15", "2", "","", "NULLABLE")
        
	with arcpy.da.UpdateCursor(out_name,["PercentArea","Kc_Medio","Kc_Enero","Kc_Febrero","Kc_Marzo","Kc_Abril","Kc_Mayo","Kc_Junio","Kc_Julio","Kc_Agosto","Kc_Septiembre","Kc_Octubre","Kc_Noviembre","Kc_Diciembre"]) as rows:
                        for row in rows:
                                row[1] = 0.0283 + (0.0203*row[0])-(0.00017*row[0]**2)
                                row[2] = row[1] * 0.971
                                row[3] = row[1] * 0.956
                                row[4] = row[1] * 0.971
                                row[5] = row[1] * 0.912
                                row[6] = row[1] * 0.809
                                row[7] = row[1] * 0.912
                                row[8] = row[1] * 1
                                row[9] = row[1] * 1.162
                                row[10] = row[1] * 1.088
                                row[11] = row[1] * 1.235
                                row[12] = row[1] * 1.074
                                row[13] = row[1] * 0.926
                                rows.updateRow(row)

def calculoEto(out_name,Var0,Var1,Var2,x,shapeFile,eto,etoPrev,LstMeses,contador,gdbPath,leto,tempFile):

        print("Obteniendo ETo de los mapas de prediccion\n")

        arcpy.CreateTable_management("in_memory", "Tabla", "", "")
	arcpy.AddField_management("Tabla", "Identificador_Eto", "DOUBLE", "15", "2", "","", "NULLABLE")

	for mes in xrange(0,12):
                arcpy.AddField_management("Tabla", "Eto_{0}".format(LstMeses[mes]), "DOUBLE", "15", "2", "","", "NULLABLE")
        del mes

        for fid in xrange(int(Var1), int(Var2)+1):
                for mes in xrange(0,12):
			arcpy.MakeFeatureLayer_management(shapeFile, "layer{0}{1}".format(fid,LstMeses[mes]), "FID ={0}".format(fid))
        	        arcpy.Clip_management("I:\\MapasKrig\\rr_{0}".format(LstMeses[mes]),"#","eR{0}{1}".format(fid,LstMeses[mes]),"layer{0}{1}".format(fid,LstMeses[mes]),"0","ClippingGeometry")
                
                	rstArray = arcpy.RasterToNumPyArray("eR{0}{1}".format(fid,LstMeses[mes]))
                        Array = numpy.array(rstArray, numpy.dtype([('Value', numpy.float32)]))
                        arcpy.da.NumPyArrayToTable(Array,"{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],fid))

	                with arcpy.da.SearchCursor("{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],fid), ["value"]) as rows:
        	        	for row in rows:
                	        	x += row[0]
                        	        if row[0] != 0:
                                		contador += 1
                        try:
                                eto = x / contador
                                etoPrev.insert(mes,eto)
                                if len(etoPrev) > 12:
                                        etoPrev.pop()
                        except: 
                                eto = etoPrev[mes]
                                leto.append(eto)
                                contador = 0
                                x=0
                                continue

                        leto.append(eto)
                        contador = 0
                        x=0
                        arcpy.Delete_management("{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],fid))

		with arcpy.da.InsertCursor("Tabla",["Identificador_Eto","Eto_enero","Eto_febrero","Eto_marzo","Eto_abril","Eto_mayo","Eto_junio","Eto_julio","Eto_agosto","Eto_septiembre","Eto_octubre","Eto_noviembre","Eto_diciembre"]) as cursor:
                	cursor.insertRow((fid,leto[0],leto[1],leto[2],leto[3],leto[4],leto[5],leto[6],leto[7],leto[8],leto[9],leto[10],leto[11]))
		leto=[]
            
        arcpy.Delete_management("eR{0}{1}".format(fid,LstMeses[mes]))
        arcpy.Delete_management("layer{0}{1}".format(fid,LstMeses[mes]))
        del mes

def calculoEtc(Var0,Var1,Var2,LstMeses,x,gdbPath,leto,contador,out_name):
        
        print("Calculando ETc\n")

        arcpy.MakeTableView_management("Tabla", "{0}_ETo".format(Var0))
	arcpy.MakeTableView_management(out_name, "T_{0}".format(Var0))
        arcpy.AddJoin_management("T_{0}".format(Var0), "Identificador", "{0}_ETo".format(Var0), "Identificador_Eto", "KEEP_COMMON")
        arcpy.TableToTable_conversion("T_{0}".format(Var0), "in_memory", "{0}_Tabla".format(Var0))
        
        for mes in xrange(0,12):
		arcpy.AddField_management("{0}_Tabla".format(Var0), "Etc_{0}".format(LstMeses[mes]), "DOUBLE", "15", "2", "","", "NULLABLE")
                
        for mes in xrange(0,12):
                with arcpy.da.SearchCursor("{0}_Tabla".format(Var0),["Kc_{0}".format(LstMeses[mes]),"Tabla_Eto_{0}".format(LstMeses[mes])]) as rows:
         		for row in rows:
				try:
                                	x = row[0] * row[1]
                                	leto.append(x)
				except:
					continue

		with arcpy.da.UpdateCursor("{0}_Tabla".format(Var0),["Etc_{0}".format(LstMeses[mes])]) as rows:
                        for row in rows:
                                try:
					row[0] = leto[contador]
                                	rows.updateRow(row)
                                	contador += 1
				except:
					continue
				
                leto=[]         
                contador = 0
        del mes
        
def calculoNtr(out_name,Var0,Var1,Var2,x,shapeFile,pe,pePrev,LstMeses,contador,gdbPath,lpe,tempFile):
        
        print("Calculando Necesidades Teoricas de Riego\n")

        for mes in xrange(0,12):
		arcpy.MakeFeatureLayer_management(shapeFile, "layer{0}{1}".format(Var0,LstMeses[mes]), "TM ={0}".format(Var0))
                arcpy.Clip_management("I:\\MapasPe\\rr_{0}".format(LstMeses[mes]),"#","eR{0}{1}".format(Var0,LstMeses[mes]),"layer{0}{1}".format(Var0,LstMeses[mes]),"0","ClippingGeometry")
                
                rstArray = arcpy.RasterToNumPyArray("eR{0}{1}".format(Var0,LstMeses[mes]))
                Array = numpy.array(rstArray, numpy.dtype([('Value', numpy.float32)]))
                arcpy.da.NumPyArrayToTable(Array,"{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],Var0))

                with arcpy.da.SearchCursor("{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],Var0), ["value"]) as rows:
                        for row in rows:
				x += row[0]
                                if row[0] != 0:
                                        contador += 1
                try:
                        pe = x / contador
                        pePrev.insert(mes,pe)
                        if len(pePrev) > 12:
                                pePrev.pop()
                except: 
                        pe = pePrev[mes]
                        lpe.append(pe)
                        contador = 0
                        x=0
                        continue
                lpe.append(pe)
                contador = 0
                x=0

                arcpy.Delete_management("{0}outputFile_{1}{2}.dbf".format(tempFile,LstMeses[mes],Var0))

		if lpe[mes] > 75:
			Pe = 0.8 * lpe[mes] - 25
		if lpe[mes] < 75:
			Pe = 0.6 * lpe[mes] - 10
		lpe.append(pe)

		arcpy.AddField_management("{0}_Tabla".format(Var0), "Ntr_{0}".format(LstMeses[mes]), "DOUBLE", "15", "2", "","", "NULLABLE")

        	with arcpy.da.UpdateCursor("{0}_Tabla".format(Var0),["Etc_{0}".format(LstMeses[mes]),"Ntr_{0}".format(LstMeses[mes])]) as rows:
			for row in rows:
				try:
					row[1] = row[0] - lpe[mes]
					rows.updateRow(row)
				except:
					print("none")
					continue
        lpe = []

	arcpy.TableToTable_conversion("{0}_Tabla".format(Var0), gdbPath, "Tabla_{0}".format(Var0))
	
	arcpy.AddField_management("{0}\\Tabla_{1}".format(gdbPath,Var0), "ET1", "DOUBLE", "15", "2", "","", "NULLABLE")
	arcpy.AddField_management("{0}\\Tabla_{1}".format(gdbPath,Var0), "ET2", "DOUBLE", "15", "2", "","", "NULLABLE")
	arcpy.AddField_management("{0}\\Tabla_{1}".format(gdbPath,Var0), "ET3", "DOUBLE", "15", "2", "","", "NULLABLE")
	arcpy.AddField_management("{0}\\Tabla_{1}".format(gdbPath,Var0), "ET4", "DOUBLE", "15", "2", "","", "NULLABLE")
	
	with arcpy.da.UpdateCursor("{0}\\Tabla_{1}".format(gdbPath,Var0), ["ET1","ET2","ET3","ET4"]) as rows:
                for row in rows:
                        row[0] = 40
                        row[1] = 30
                        row[2] = 20
                        row[3] = 10
                        rows.updateRow(row)

if __name__ == '__main__':

        #Variables
        nombreTer = sys.argv[1]
        listaNombres = []
        rasters = ""
        x = 0
        contador = 0
        fieldName = ["Kc_Medio","Kc_Enero","Kc_Febrero","Kc_Marzo","Kc_Abril","Kc_Mayo","Kc_Junio","Kc_Julio","Kc_Agosto","Kc_Septiembre","Kc_Octubre","Kc_Noviembre","Kc_Diciembre"]
        LstMeses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        eto = 0
        etoPrev=[]
        leto=[]
	pe = 0
        pePrev=[]
        lpe=[]
	
        #Rutas Archivos
        rasterPath = "I:\\fotos_aereas_alicante_2007\\"
        gdbPath = "C:\\Users\\Ronny\\Documents\\ArcGIS\\Default.gdb"
        rasterTempPath = "I:\\TEMP\\"
        archivoTm = "C:\\Users\\Ronny\\Desktop\\TM.txt"
        shapeFile = "C:\\Users\\Ronny\\Desktop\\Nueva carpeta\\Simulacion_base_Sort.shp"
        tableFile = "I:\\SIG_CITRI_ALICANTE\\alicante_tabla.dbf"
        tempFile = "I:\\TEMP\\"

        #input[0,1,2,3] / Var0, Var1, Var2, rasters / Tm, FID_inicial, FID_final, rutaresters  
        input = inputs(nombreTer,listaNombres,rasters,rasterPath,contador,archivoTm)

        arcpy.env.workspace = "in_memory"
        print("Construyendo raster temporal con: \n{0}\n".format(input[3]))
        arcpy.MosaicToNewRaster_management(input[3],rasterTempPath,"rasterTemp.tif","","8_BIT_UNSIGNED","","3","FIRST","")

        rasterTemp = "{0}\\rasterTemp.tif".format(rasterTempPath)
        out_name = "Tabla_{0}".format(input[0])

        t0= time.time()

        areaSombra(out_name,input[1],input[2],rasterTemp,x,shapeFile)
        coeficienteCultivo(out_name,gdbPath,fieldName,input[0],tableFile)
        calculoEto(out_name,input[0],input[1],input[2],x,shapeFile,eto,etoPrev,LstMeses,contador,gdbPath,leto,tempFile)
        calculoEtc(input[0],input[1],input[2],LstMeses,x,gdbPath,leto,contador,out_name)
	calculoNtr(out_name,input[0],input[1],input[2],x,shapeFile,pe,pePrev,LstMeses,contador,gdbPath,lpe,tempFile)

        print("Terminado en {0}".format(str(timedelta(seconds=int(time.time() - t0)))))
        
