#Abaqus modules
from abaqus import *
from abaqusConstants import *


#=======================================================#
#=======================================================#
#                   CONTROLS                            #
#=======================================================#
#=======================================================#


mdbName      = 'Static'
cpus         = 1			#Number of CPU's
run          = 1
post         = 1			#Run post prossesing
monitor      = 0

#4x4  x10(5)
x            = 2			#Nr of columns in x direction
z            = 2			#Nr of columns in z direction
y            = 1			#nr of stories

#Static step
staticType   = 'general' 	#'general' or 'riks'
nlg          = ON				# Nonlinear geometry (ON/OFF)
inInc        = 0.1				# Initial increment
minIncr      = 1e-9
maxStaticInc = 50 #Maximum number of increments for static step

#Live load
LL_kN_m      = -2.0	    #kN/m^2 (-2.0)


#Post
defScale = 10
printFormat = PNG 	#TIFF, PS, EPS, PNG, SVG





#============================================================#
#============================================================#
#                   PERLIMINARIES                            #
#============================================================#
#============================================================#

#=========== Import modules  ============#

import os
import glob
from datetime import datetime

import myFuncs
reload(myFuncs)


#=========== Other stuff  ============#

#Makes mouse clicks into physical coordinates
session.journalOptions.setValues(replayGeometry=COORDINATE,
	recoverGeometry=COORDINATE)

#Print begin script to console
print '\n'*6
print '###########    NEW SCRIPT    ###########'
print str(datetime.now())[:19]

#Print status to console during analysis
if monitor:
	myFuncs.printStatus(ON)

#Create text file to write results in
with open('results.txt', 'w') as f:
	None






#==========================================================#
#==========================================================#
#                   Build model                            #
#==========================================================#
#==========================================================#


#=========== Set up model  ============#
modelName = "staticMod"
matFile = 'mat_1.inp'

#Create model based on input material
print '\n'*2
mdb.ModelFromInputFile(name=modelName, inputFileName=matFile)
print '\n'*2

#For convinience
M = mdb.models[modelName]
ass = M.rootAssembly
'''
M and ass are used as object cointaining the model and the assembly of
that model. If a new model is created they needs to be updated.
This is just for faster writing and easier copy pasting of code. 
'''

#Deletes all other models
myFuncs.delModels(modelName)

#Close and delete old jobs and ODBs
myFuncs.delJobs(exeption = matFile)


#=========== Material  ============#
#Material names
steel = 'DOMEX_S355'
concrete = 'Concrete'
rebarSteel = 'Rebar Steel'

myFuncs.createMaterials(M, mat1=steel, mat2=concrete, mat3=rebarSteel)


#=========== Parts  ============#
#Create Column
col_height = 4000.0
myFuncs.createColumn(M, height=col_height, mat=steel, partName='COLUMN')

#Create Beam
beam_len = 8000.0
myFuncs.createBeam(M, length=beam_len, mat=steel, partName='BEAM')

#Create slab
myFuncs.createSlab(M, t=200.0, mat=concrete, dim=beam_len,
	rebarMat=rebarSteel, partName='SLAB')


#=========== Sets and surfaces  ============#
#A lot of surfaces are created with the joints
myFuncs.createSets(M, col_height)
myFuncs.createSurfs(M)


#=========== Assembly  ============#
myFuncs.createAssembly(M, x, z, y,
	x_d = beam_len, z_d = beam_len, y_d = col_height)


#=========== Mesh  ============#
seed = 800.0
myFuncs.mesh(M, seed)

#Write nr of elements to results file
M.rootAssembly.regenerate()
nrElm = myFuncs.elmCounter(M)
with open('results.txt','a') as f:
	f.write("Total nr of elements: %s" %nrElm)


#=========== Joints  ============#
myFuncs.createJoints(M, x, z, y,
	x_d = beam_len, z_d = beam_len, y_d = col_height)


#=========== Fix column base  ============#
myFuncs.fixColBase(M, x, z)




#===================================================#
#===================================================#
#               STEP AND DEPENDENCIES           	#
#===================================================#
#===================================================#

#=========== Static step  ============#
oldStep = 'Initial'
stepName = 'staticStep'

if staticType == 'general':
	M.StaticStep(name=stepName, previous=oldStep, 
		nlgeom=nlg,
		initialInc=inInc, minInc=minIncr, maxNumInc=maxStaticInc)
elif staticType == 'riks':
	M.StaticRiksStep(name=stepName, previous=oldStep, 
		nlgeom=nlg,
		initialArcInc=inInc, minArcInc=minIncr, maxNumInc=maxStaticInc,
		maxLPF=1.0)



#=========== History output  ============#
M.rootAssembly.regenerate()

#Delete default history output
del M.historyOutputRequests['H-Output-1']

#Create history output for energies
M.HistoryOutputRequest(name='Energy', 
	createStepName=stepName, variables=('ALLIE', 'ALLKE', 'ALLWK'),)



#=========== Loads  ============#
# Gravity
M.Gravity(comp2=-9800.0, createStepName=stepName, 
    distributionType=UNIFORM, field='', name='Gravity')

#LL
LL=LL_kN_m * 1.0e-3   #N/mm^2
myFuncs.addSlabLoad(M, x, z, y, stepName, load = LL)





#===========================================================#
#===========================================================#
#                   JOB AND POST                            #
#===========================================================#
#===========================================================#

M.rootAssembly.regenerate()

#Save model
mdb.saveAs(pathName = mdbName + '.cae')

#Create job
mdb.Job(model=modelName, name=modelName,
    numCpus=cpus, numDomains=cpus,
    explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE)

#Run job
if run:
	myFuncs.runJob(modelName)


#=========== Post proccesing  ============#
if post:

	print 'Post processing...'

	#Clear plots
	for plot in session.xyPlots.keys():
		del session.xyPlots[plot]

	#=========== Contour  ============#
	myFuncs.countourPrint(modelName, defScale, printFormat)

	#=========== XY  ============#
	myFuncs.xyEnergyPrint(modelName, printFormat)


	print '   done'



print '###########    END OF SCRIPT    ###########'