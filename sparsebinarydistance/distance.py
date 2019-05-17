#!/usr/bin/env python3
import pandas as pd
import numpy as np

def sparseDistance( X, minPresence=1, minMeasurementsPerCell=1, weight=True ):
    """Calculate a distance matrix based on a boolean sparse cells/observations matrix

    Parameters
    ----------
    X : pandas dataframe
        sparse boolean cell by observation matrix, contains 1s 0s and NaNs for missing data
    minPresence : int
        mimumum amount of 1s or zeros present per feature, lower sums are pruned
    minMeasurementsPerCell : int
        minimum of total observations per cell


    Returns
    -------
    keptX : pandas dataframe
        Cell by observation matrix with only the cells and features which have been kept

    jointMatrix : numpy matrix
        Cell by cell distance matrix where the Similarity and Difference have been combined


    simMatrix : numpy matrix
        Similarity matrix

    differenceMatrix: numpy matrix
        Difference matrix

    normalisationFactor : numpy vector
        Weight per feature
    """

    prev= None
    selectedCells=None
    keptX = X.copy()
    while prev is None or prev[0]!=sum(selectedCells) or prev[1]!=sum(selectedColumns):
        if selectedCells is not None:
            prev = (sum(selectedCells), sum(selectedColumns))
        selectedCells = (keptX>=0).sum(axis=1) >= minMeasurementsPerCell # Select only cells/rows with at least one measurement
        selectedColumns = ((keptX[selectedCells]==1).sum(axis=0)>=minPresence) & ((keptX[selectedCells]==0).sum(axis=0)>0)
        #print( f'We have {sum(selectedCells)} rows and {sum(selectedColumns)} X left' )
        keptX = keptX[selectedCells].loc[:,selectedColumns]

    if keptX.shape[0]<2:
        raise ValueError('Not enough data')

    pOnes = []
    pZeros = []
    for feature in keptX.columns:
        # Weights:
        column = keptX[feature]
        if weight:
            pOnes.append( -np.log2( ( np.sum(column==1)/len(column) )**2 ) ) #probability of two cells both having feature
            pZeros.append( -np.log2( ( np.sum(column==0)/len(column) )**2 ) )#probability of two cells not having feature,  (and we know it)
        else:
            pOnes.append( -np.log2( ( 0.5 )**2 ) ) #probability of two cells both having feature
            pZeros.append( -np.log2( (0.5)**2 ))

    pOnes = np.array(pOnes)
    pZeros = np.array(pZeros)
    #print( np.sum(np.isnan(pZeros)), np.sum(np.isnan(pOnes)),  np.min(pZeros), np.min(pOnes))
    #print(keptX.shape)
    rawMatrix = keptX.values

    #return rawMatrix
    iteration = 0

    # Similarity: how much do cells look alike?
    simMatrix =  np.zeros( (rawMatrix.shape[0], rawMatrix.shape[0]) )
    # What is the difference between the cells?
    differenceMatrix =  np.zeros( (rawMatrix.shape[0], rawMatrix.shape[0]) )

    jointMatrix = np.zeros( (rawMatrix.shape[0], rawMatrix.shape[0]) )

    mv = int((len(jointMatrix)*(len(jointMatrix)-1))/2)

    for cai in range(rawMatrix.shape[0]):
        a = rawMatrix[cai,:]

        for cbi in range(rawMatrix.shape[0]):
            b = rawMatrix[cbi,:]

            # Un normalized distance
            pairwiseUnnormalizedDistance = np.logical_and( a==1, b==0 ) * \
            (pOnes + pZeros) + \
             np.logical_and( a==0, b==1 ) * (pZeros + pOnes) # For different batches the pOnes/pZeros is batch depended

            # Normalize the distance:
            normalisationFactor = np.sum( pOnes* (a==1)) + np.sum( pZeros*(a==0)) + \
                    np.sum( pOnes* (b==1)) + np.sum( pZeros* (b==0))

            pairwiseNormalizedDistance = np.sum(pairwiseUnnormalizedDistance) / (
                    normalisationFactor )
            differenceMatrix[cai, cbi] = pairwiseNormalizedDistance

            # Similarity calculation:
            sim = np.sum( (pOnes+pOnes) * np.logical_and( a==1, b==1 )) + \
                  np.sum( (pZeros+pZeros)*np.logical_and( a==0, b==0 ))

            normalisedSim = sim/normalisationFactor
            simMatrix[cai, cbi] = normalisedSim

            joinedDistance =  pairwiseNormalizedDistance + (1-normalisedSim )
            jointMatrix[cai,cbi]= joinedDistance


            if cai==cbi:
                break

    for i in range(jointMatrix.shape[0]):
        for j in range(jointMatrix.shape[0]):
            jointMatrix[j,i]=jointMatrix[i,j]
            if i==j:
                break
    jointMatrix = pd.DataFrame(jointMatrix)
    jointMatrix.index = keptX.index
    jointMatrix.columns = keptX.index

    simMatrix = pd.DataFrame(simMatrix)
    simMatrix.index = keptX.index
    simMatrix.columns = keptX.index

    differenceMatrix = pd.DataFrame(differenceMatrix)
    differenceMatrix.index = keptX.index
    differenceMatrix.columns = keptX.index
    return keptX, jointMatrix, simMatrix, differenceMatrix, normalisationFactor
