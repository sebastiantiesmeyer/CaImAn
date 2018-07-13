#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 25 11:24:18 2018

@author: sebastian
"""

import argparse
import os
import psutil

import numpy as np
import caiman as cm
from caiman.source_extraction import cnmf
from caiman.utils.utils import save_object


def extract_spikes(file, destination,bord_px=0):
    
    print("Extracting spikes from "+file+" and saving to "+destination)
    
    # stop the cluster if one exists
    n_processes = psutil.cpu_count()//2
    print('using ' + str(n_processes) + ' processes')
    print("Stopping  cluster to avoid unnencessary use of memory....")
     
    
    # START CLUSTER
    if 'dview' in locals():
        cm.stop_server(dview=dview)
    c, dview, n_processes = cm.cluster.setup_cluster(
        backend='local', n_processes=n_processes, single_thread=False)   
    
    
    
    # parameters for source extraction and deconvolution
    p = 1               # order of the autoregressive system
    K = None            # upper bound on number of components per patch, in general None
    gSig = 3            # gaussian width of a 2D gaussian kernel, which approximates a neuron
    gSiz = 13           # average diameter of a neuron, in general 4*gSig+1
    merge_thresh = .7   # merging threshold, max correlation allowed
    rf = 40             # half-size of the patches in pixels. e.g., if rf=40, patches are 80x80
    stride_cnmf = 20    # amount of overlap between the patches in pixels
    #                     (keep it at least large as gSiz, i.e 4 times the neuron size gSig)
    tsub = 2            # downsampling factor in time for initialization,
    #                     increase if you have memory problems
    ssub = 1            # downsampling factor in space for initialization,
    #                     increase if you have memory problems
    Ain = None          # if you want to initialize with some preselected components
    #                     you can pass them here as boolean vectors
    low_rank_background = True  # None leaves background of each patch intact,
    #                             True performs global low-rank approximation 
    gnb = 10            # number of background components (rank) if positive,
    #                     else exact ring model with following settings
    #                         gnb=-2: Return background as b and W
    #                         gnb=-1: Return full rank background B
    #                         gnb= 0: Don't return background
    nb_patch = 10       # number of background components (rank) per patch,
    #                     use 0 or -1 for exact background of ring model (cf. gnb)
    min_corr = .8       # min peak value from correlation image
    min_pnr = 10        # min peak to noise ration from PNR image
    ssub_B = 2          # additional downsampling factor in space for background
    ring_size_factor = None #1.4  # radius of ring is gSiz*ring_size_factor    
    
    # load memory mappable file
    Yr, dims, T = cm.load_memmap(file)
    Y = Yr.T.reshape((T,) + dims, order='F')
    
    cnm = cnmf.CNMF(n_processes=n_processes,
                method_init='corr_pnr',             # use this for 1 photon
                k=K,
                gSig=(gSig, gSig),
                gSiz=(gSiz, gSiz),
                merge_thresh=merge_thresh,
                p=p,
                dview=dview,
                tsub=tsub,
                ssub=ssub,
                Ain=Ain,
                rf=rf,
                stride=stride_cnmf,
                only_init_patch=True,               # just leave it as is
                gnb=gnb,
                nb_patch=nb_patch,
                method_deconvolution='oasis',       # could use 'cvxpy' alternatively
                low_rank_background=low_rank_background,
                update_background_components=True,  # sometimes setting to False improve the results
                min_corr=min_corr,
                min_pnr=min_pnr,
                normalize_init=False,               # just leave as is
                center_psf=True,                    # leave as is for 1 photon
                ssub_B=ssub_B,
                ring_size_factor=ring_size_factor,
                del_duplicates=True,                # whether to remove duplicates from initialization
                border_pix=bord_px)                 # number of pixels to not consider in the borders
    cnm.fit(Y)
    
    print("Extraction completed, saving object.")
    #cnm.dview=None
    save_object(cnm,destination)
     


def get_job_type(job):
    extension = [e for e in job.split('.')]
    if len(extension)==1:
        return 'folder'
    elif extension[-1]=='mmap':
        return 'mmap'
    else:
        print("Unknown file extension; exiting with 0")
        exit()



if __name__ == "__main__":
    
    
    parser = argparse.ArgumentParser(description='Ca2+ motion corrections script.')
    parser.add_argument('input', metavar='N', type=str, nargs='+',
                       help='Pipeline input: file name or folder root name')
    parser.add_argument('--output', '-o', type=str, nargs=1,
                       help='Onput location; default: . ', default = '.')
    
    jobs = parser.parse_args().input
    

    job_type = get_job_type(jobs[0])
    
    if len(jobs)>1:
        output_loc=jobs[1]
    else:
        output_loc = parser.parse_args().output[0]
        
    if job_type=='folder':
        root = jobs[0]
        
        mice = [f for f in os.listdir(os.path.join(root,'cropped')) if os.path.isdir(os.path.join(root,'cropped',f))]
        for mouse in mice:
            days = [f for f in os.listdir(os.path.join(root,'cropped',mouse)) if os.path.isdir(os.path.join(root,'cropped',mouse,f))]
            for day in days:
                files = [f for f in os.listdir(os.path.join(root,'cropped',mouse,day)) if f[-4:]=='.tif']
                for file in files:
                    dest_name = '_'.join([mouse,day,'corrected']+'.pkl')
                    os.system('mkdir -p '+os.path.join(root,'motion_corr',mouse,day))
                    if not([f for f in os.listdir(os.path.join(root,'motion_corr',mouse,day)) if dest_name in f]):
                        dest = (os.path.join(root,'motion_corr',mouse,day,dest_name))
                        file = (os.path.join(root,'cropped',mouse,day,file))
                        extract_spikes(file,dest)
    
    else:
        extract_spikes(jobs[0],output_loc)
            
        
        
