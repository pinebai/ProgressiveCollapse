#Abaqus modules
from abaqus import *
from abaqusConstants import *
from regionToolset import *


#=======================================================#
#=======================================================#
#                   CONTROLS                            #
#=======================================================#
#=======================================================#


mdbName        = 'exp2'
cpus           = 1			#Number of CPU's
monitor        = 1


run            = 1
stepTime       = 1.0

load = 2.0e3 #N/mm


#Post
defScale       = 1.0
printFormat    = PNG 	#TIFF, PS, EPS, PNG, SVG
fieldIntervals = 100
histIntervals  = 100
animeFrameRate = 5




#==========================================================#
#==========================================================#
#                   Perliminary                            #
#==========================================================#
#==========================================================#

import lib.func as func
import lib.beam as beam
import lib.singleCol as singleCol
reload(func)
reload(beam)
reload(singleCol)

modelName   = mdbName

steel = 'DOMEX_S355'
concrete = 'Concrete'
rebarSteel = 'Rebar Steel'

#Set up model with materials
func.perliminary(monitor, modelName)

M=mdb.models[modelName]




#==========================================================#
#==========================================================#
#                   Build model                            #
#==========================================================#
#==========================================================#

#Build geometry
singleCol.createSingleBeam(modelName)


#Create setp
oldStep = 'Initial'
stepName = 'load'
M.ExplicitDynamicsStep(name=stepName, previous=oldStep, 
    timePeriod=stepTime) 

#Create smooth step
M.SmoothStepAmplitude(name='smooth', timeSpan=STEP, data=(
	(0.0, 0.0), (0.9*stepTime, 1.0)))

#Add line load
M.LineLoad(comp1=load, createStepName=stepName, name=
    'LineLoad', amplitude='smooth', region=Region(
    edges=M.rootAssembly.instances['COLUMN-1'].edges.findAt(
    ((0.0, 375.0, 0.0), ), ((0.0, 1875.0, 0.0), ), )))


#=====================================================#
#=====================================================#
#                   Output                            #
#=====================================================#
#=====================================================#

#Frequency of field output
M.fieldOutputRequests['F-Output-1'].setValues(numIntervals=fieldIntervals)

M.FieldOutputRequest(name='damage', 
    createStepName=stepName, variables=('SDEG', 'DMICRT', 'STATUS'),
    numIntervals=fieldIntervals)

#Delete default history output
del M.historyOutputRequests['H-Output-1']


#History output
regionDef=M.rootAssembly.allInstances['COLUMN-1'].sets['col-base']
M.HistoryOutputRequest(name='load-base', 
    createStepName=stepName, variables=('RF1', ), region=regionDef, 
    numIntervals=histIntervals)

regionDef=M.rootAssembly.allInstances['COLUMN-1'].sets['col-top']
M.HistoryOutputRequest(name='load-top', 
    createStepName=stepName, variables=('RF1', ), region=regionDef, 
    numIntervals=histIntervals)

regionDef=M.rootAssembly.allInstances['COLUMN-1'].sets['col-mid']
M.HistoryOutputRequest(name='displacement', 
    createStepName=stepName, variables=('U1', ), region=regionDef, 
    numIntervals=histIntervals)



#===========================================================#
#===========================================================#
#                   Save and run                            #
#===========================================================#
#===========================================================#
M.rootAssembly.regenerate()
#Save model
mdb.saveAs(pathName = mdbName + '.cae')


#Create job
precision = SINGLE #SINGLE/ DOUBLE/ DOUBLE_CONSTRAINT_ONLY/ DOUBLE_PLUS_PACK
nodalOpt = SINGLE #SINGLE or FULL
mdb.Job(model=modelName, name=modelName,
	    numCpus=cpus, numDomains=cpus,
	    explicitPrecision=precision, nodalOutputPrecision=nodalOpt)

#Run job
if run:
	func.runJob(modelName)
	#Write CPU time to file
	func.readStaFile(modelName, 'results.txt')



#===================================================#
#===================================================#
#                   Post                            #
#===================================================#
#===================================================#

	print 'Post processing...'

	#Clear plots
	for plot in session.xyPlots.keys():
		del session.xyPlots[plot]

	#=========== Contour  ============#
	# func.countourPrint(modelName, defScale, printFormat)

	#=========== Animation  ============#
	# func.animate(modelName, defScale, frameRate= animeFrameRate)
	
	#=========== XY  ============#
	singleCol.xySimple(modelName, printFormat)

	print '   done'


print '###########    END OF SCRIPT    ###########'
