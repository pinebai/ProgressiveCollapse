#Abaqus modules
from abaqus import *
from abaqusConstants import *


#=======================================================#
#=======================================================#
#                   CONTROLS                            #
#=======================================================#
#=======================================================#


modelName      = 'apBeamImp15st'
cpus           = 8			#Number of CPU's

run            = 1

parameter      = 0
runPara        = 0

forceCollapse  = 0



#=========== Geometry  ============#
#Size
x              = 4			#Nr of columns in x direction
z              = 4			#Nr of columns in z direction
y              = 15			#nr of stories


#=========== Static step  ============#
static_Type    = 'general' 	#'general' or 'riks'
static_InInc   = 0.1		# Initial increment
static_MinIncr = 1e-9		# Smalles allowed increment
static_maxInc  = 50 		#Maximum number of increments 


#=========== Implicit step  ============#
#Single APM
APMcol        = 'COLUMN_D4-1'

rmvStepTime   = 20e-3		
dynStepTime   = 2.0

dynamic_InInc = 0.1
dynamic_MaxInc= 500


#Itterations, not in use
itterations   = 0
elsetName     = None
var           = 'PEEQ' #'S'
var_invariant = None #'mises'
limit         = 0.1733	#Correct limit for PEEQ = 0.1733



#=========== Force collapse  ============#
loadTime       = 5.0
loadFactor     = 35.0



#=========== General  ============#
monitor        = 0			#Write status of job continusly in Abaqus CAE

#Live load
LL_kN_m        = -0.5	    #kN/m^2 (-2.0)

#Mesh
seed           = 750.0		#Global seed
slabSeedFactor = 1			#Change seed of slab
steelMatFile   = 'mat_75.inp'  #Damage parameter is a function of element size

#Post
defScale       = 1.0
printFormat    = PNG 		#TIFF, PS, EPS, PNG, SVG
animeFrameRate = 5



#==========================================================#
#==========================================================#
#                   Perliminary                            #
#==========================================================#
#==========================================================#

import lib.func as func
import lib.beam as beam
reload(func)
reload(beam)

mdbName        = 'apBeamImp'    	#Name of .cae file


#Set up model with materials
func.perliminary(monitor, modelName, steelMatFile)

M=mdb.models[modelName]




#==========================================================#
#==========================================================#
#                   Build model                            #
#==========================================================#
#==========================================================#

#Build geometry
beam.buildBeamMod(modelName, x, z, y, seed, slabSeedFactor)



#=========== Static step  ============#
oldStep = 'Initial'
stepName = 'static'
if static_Type == 'general':
	M.StaticStep(name=stepName, previous=oldStep, 
		nlgeom=ON, initialInc=static_InInc, minInc=static_MinIncr,
		maxNumInc=static_maxInc)
elif static_Type == 'riks':
	M.StaticRiksStep(name=stepName, previous=oldStep, 
		nlgeom=ON, initialArcInc=static_InInc, minArcInc=static_MinIncr,
		maxNumInc=static_maxInc, maxLPF=1.0)



# Gravity
M.Gravity(comp2=-9800.0, createStepName=stepName, 
	distributionType=UNIFORM, field='', name='Gravity')

#LL
LL=LL_kN_m * 1.0e-3   #N/mm^2
func.addSlabLoad(M, x, z, y, stepName, LL)


#Detete default output
del M.fieldOutputRequests['F-Output-1']
del M.historyOutputRequests['H-Output-1']

#Displacement field output
M.FieldOutputRequest(name='U', createStepName=stepName, 
    variables=('U', ))
M.FieldOutputRequest(name='Status', createStepName=stepName, 
    variables=('STATUS', ))

#Field output: damage
# M.FieldOutputRequest(name='damage', 
    # createStepName=stepName, variables=('SDEG', 'DMICRT', 'STATUS'))

#Create history output for energies
M.HistoryOutputRequest(name='Energy', 
	createStepName=stepName, variables=('ALLIE', 'ALLKE'),)

#R2 at all col-bases
M.HistoryOutputRequest(createStepName='static', name='R2',
	region=M.rootAssembly.sets['col-bases'], variables=('RF2', ))


#U2 at top of column to later be removed
M.HistoryOutputRequest(name=APMcol+'_top'+'U', 
		createStepName=stepName, variables=('U2',), 
		region=M.rootAssembly.allInstances[APMcol].sets['col-top'])




#=========== Coulumn removal step  ============#

# Create step for column removal
oldStep = stepName
stepName = 'elmRemStep'
M.ImplicitDynamicsStep( name=stepName,  previous=oldStep, 
	initialInc=rmvStepTime, maxNumInc=50,
	timeIncrementationMethod=FIXED, timePeriod=rmvStepTime,
	nlgeom=ON)

#Remove column
rmvSet = APMcol+'.set'
M.ModelChange(activeInStep=False, createStepName=stepName, 
	includeStrain=False, name='elmRemoval', region=
	M.rootAssembly.sets[rmvSet], regionType=GEOMETRY)



#=========== Dynamic step  ============#

#Create dynamic APM step
oldStep = stepName
stepName = 'dynamicStep'
M.ImplicitDynamicsStep(initialInc=dynamic_InInc, minInc=5e-07, name=
	stepName, previous=oldStep, timePeriod=dynStepTime, nlgeom=ON,
	maxNumInc=dynamic_MaxInc)





#=========== Force collapse   ============#

if forceCollapse:
	#Create new loading step
	oldStep = stepName
	stepName='loading'
	M.ImplicitDynamicsStep(initialInc=0.01, minInc=0.0001,
		name=stepName, previous=oldStep, timePeriod=loadTime, nlgeom=ON,
		maxNumInc=dynamic_MaxInc)


	#Create linear amplitude
	M.TabularAmplitude(data=((0.0, 1.0), (loadTime, loadFactor)), 
	    name='linIncrease', timeSpan=STEP)

	#Change amplitude of slab load in force step
	func.changeSlabLoad(M, x, z, y, stepName, amplitude='linIncrease')










#=========== Save and run  ============#
M.rootAssembly.regenerate()

#Save model

#Create job
mdb.Job(model=modelName, name=modelName, numCpus=cpus, numDomains=cpus)

#Run job
if run:
	mdb.saveAs(pathName = mdbName + '.cae')
	func.runJob(modelName)
	#Write CPU time to file
	func.readMsgFile(modelName, 'results.txt')



#=========== Post  ============#
	print 'Post processing...'

	
	# #Contour
	# func.countourPrint(modelName, defScale, printFormat)

	#Energy
	func.xyEnergyPlot(modelName)

	#R2 at col base
	beam.xyColBaseR2(modelName,x,z)

	#Displacement at colTop
	beam.xyAPMcolPrint(modelName, APMcol)
 

	# #Check largest peeq against criteria
	# print '\n' + "Getting data from ODB..."
	# elmOverLim = func.getElmOverLim(modelName, var,
	# stepName, var_invariant, limit)
	# print "    done"
	# with open('results.txt','a') as f:
	# 	if elmOverLim:
	# 		num = len(elmOverLim)
	# 		f.write('%s	Nr of elements over lim: %s' %(modelName, num))
	# 	else: 
	# 		f.write('%s	No element over limit' %(modelName))




	print '   done'




#==============================================================#
#==============================================================#
#                   PARAMETER STUDY                            #
#==============================================================#
#==============================================================#

oldMod = modelName

if parameter:
		
	#=========== Seed  ============#
	paraLst = [1500, 500, 300]


	for para in paraLst:
		
		#New model
		modelName = 'beamAPimpSeed'+str(para)
		mdb.Model(name=modelName, objectToCopy=mdb.models[oldMod])
		M = mdb.models[modelName]	


		#=========== Change parameter  ============#
		
		beam.mesh(M, seed = para, slabSeedFactor=1.0)

		M.rootAssembly.regenerate()




		#=========== Create job and run  ============#
		#Create job
		mdb.Job(model=modelName, name=modelName,
		    numCpus=cpus, numDomains=cpus)


		if runPara:
			#Run job

			mdb.saveAs(pathName = mdbName + '.cae')
			func.runJob(modelName)
			#Write CPU time to file
			func.readMsgFile(modelName, 'results.txt')



			#=========== Post proccesing  ============#

			print 'Post processing...'
					
			# #Contour
			# func.countourPrint(modelName, defScale, printFormat)

			# #Animation
			# func.animate(modelName, defScale, frameRate= animeFrameRate)

			#Energy
			func.xyEnergyPlot(modelName)

			#R2 at col base
			beam.xyColBaseR2(modelName,x,z)

			#Displacement at colTop
			beam.xyAPMcolPrint(modelName, APMcol)


































#==========================================================#
#==========================================================#
#                   ITTERATIONS                            #
#==========================================================#
#==========================================================#
if itterations:

	#Original Names
	originModel = modelName
	originLastStep = stepName

	#Check original ODB
	print '\n' + "Getting data from ODB..."
	elmOverLim = func.getElmOverLim(originModel, var,
	originLastStep, var_invariant, limit)
	print "    done"
	if not elmOverLim: print 'No element over limit'

	#Run itterations
	count = 0
	while len(elmOverLim) > 0:
		count = count + 1

		#New names
		modelName = 'impAPM-'+str(count)


		#Copy new model
		mdb.Model(name=modelName, objectToCopy=mdb.models[originModel])	
		M = mdb.models[modelName]

		#Create step for element removal
		stepName = 'elmRmv'
		M.rootAssembly.regenerate()
		M.ImplicitDynamicsStep(initialInc=rmvStepTime, maxNumInc=50, name=
			stepName, noStop=OFF, nohaf=OFF, previous=originLastStep, 
			timeIncrementationMethod=FIXED, timePeriod=rmvStepTime, nlgeom=nlg)

		func.delInstance(M, elmOverLim, stepName)

		#================ Create new step and job =============#
		#Create dynamic APM step
		oldStep = stepName
		stepName = 'implicit'
		M.ImplicitDynamicsStep(initialInc=0.01, minInc=5e-05, name=
			stepName, previous=oldStep, timePeriod=dynStepTime, nlgeom=nlg,
			maxNumInc=300)

		#Create job
		mdb.Job(model=modelName, name=modelName, numCpus=cpus,)

		#Save model
		mdb.saveAs(pathName = caeName+'.cae')

		#Run job
		func.runJob(modelName)

		#Write CPU time to file
		func.readMsgFile(modelName, 'results.txt')

		#=========== Post  ============#
		#Clear plots
		for plot in session.xyPlots.keys():
			del session.xyPlots[plot]

		#Contour
		func.countourPrint(modelName, defScale, printFormat)

		#Energy
		func.xyEnergyPrint(modelName, printFormat)

		#U2 at top of removed column to be removed
		func.xyAPMcolPrint(modelName, APMcol, printFormat, stepName)

		#Animation
		func.animate(modelName, defScale, frameRate= 1)
		mdb.saveAs(pathName = mdbName+'.cae')


		#================ Check new ODB ==========================#
		oldODB = modelName
		print '\n' + "Getting data from ODB..."
		elmOverLim = func.getElmOverLim(modelName, var,
			originLastStep, var_invariant, limit)
		print "    done"
		if len(elmOverLim) == 0:
			print 'Req	uired itterations: %s' % (count)



print '###########    END OF SCRIPT    ###########'
