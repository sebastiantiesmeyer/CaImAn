#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 23 15:46:56 2018

@author: stiesmeyer
"""

import os
import caiman as cm
import numpy as np
import h5py
import matplotlib.pyplot as plt 

root = '/scratch/stiesmeyer/data/motion_corr'
#files = sorted([f for f in os.listdir(root) if '.mmap' in f])
files = sorted([f for f in os.listdir(root) if '.mmap' in f and len(f.split('_'))==14 and f.split('_')[1][-2:]!='17'])

target = '/scratch/stiesmeyer/data/testMovieAnalysis/results' 

week_dict = {'20170710':'1','20170711':'1','20170712':'1','20170713':'1','20170714':'1',
             '20170717':'2','20170718':'2','20170719':'2','20170720':'2','20170721':'2'
             }

week = '1'
session = 1
for i, file in enumerate(files):
    animal = file.split('_')[0]
    day = file.split('_')[1]
    if week != week_dict[day]:
        session=1
    week = week_dict[day]
    print(animal,day,week_dict[day])
        
    Yr, dims, T = cm.load_memmap(os.path.join(root,file))
    mov = cm.movie(np.array(Yr).reshape(dims[::-1]+(T,),order = 'C')[50:-50,10:-10,:])
    mov = mov.resize(0.9,1,0.9).transpose([2,0,1])
    
    os.makedirs(os.path.join(target,animal+'_w'+week,'Session'+str(session),'raw'), exist_ok=True)
    
    file = h5py.File(os.path.join(target,animal+'_w'+week,'Session'+str(session),'raw','rawMovie.h5'),'w')#'/home/sebastian/Desktop/20170710_moviedata.h5','w')
    dset=  file.create_dataset('1',mov.shape,  dtype=np.uint16, data = mov.astype(np.uint16 ))
    
    file.close()
    
    session+=1
    

#mov = cm.load('/scratch/stiesmeyer/data/testMovieAnalysis/results/32364_w1/jointExtraction/alignment/jointMovie.h5')

#from caiman import mmapping

#mov = cm.load('/scratch/stiesmeyer/data/testMovieAnalysis/results/32364_w1/jointExtraction/alignment/jointMovie.h5')


#from caiman.summary_images import correlation_pnr
#cn_filter, pnr = correlation_pnr(mov, gSig=3, swap_dim=False)



#mov.save('/scratch/stiesmeyer/data/experimental/whole_week.mmap',order='C')

    