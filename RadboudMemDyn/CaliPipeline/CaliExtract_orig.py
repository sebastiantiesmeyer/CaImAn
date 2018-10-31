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
from caiman.summary_images import correlation_pnr


dview = None

def extract_spikes(file, destination,bord_px=0, multiprocessing = False, Ain = None):
    
    global dview
    
    print("Extracting spikes from "+file+" and saving to "+destination)
    

    if multiprocessing:
        n_processes = psutil.cpu_count()//10
            # START CLUSTER
        if 'dview' in globals():
            cm.stop_server(dview=dview)
        c, dview, n_processes = cm.cluster.setup_cluster(
            backend='local', n_processes=n_processes, single_thread=False)   
        
    
    else:
        n_processes = 1
        dview = None
   
    # parameters for source extraction and deconvolution
    p = 1               # order of the autoregressive system
    K = None            # upper bound on number of components per patch, in general None
    gSig = 3            # gaussian width of a 2D gaussian kernel, which approximates a neuron
    gSiz = 4*gSig+1           # average diameter of a neuron, in general 4*gSig+1
    merge_thresh = .6   # merging threshold, max correlation allowed
    rf = 40            # half-size of the patches in pixels. e.g., if rf=40, patches are 80x80
    stride_cnmf =  20    # amount of overlap between the patches in pixels
    #                     (keep it at least large as gSiz, i.e 4 times the neuron size gSig)
    tsub = 1            # downsampling factor in time for initialization,
    #                     increase if you have memory problems
    ssub = 1            # downsampling factor in space for initialization,
    #                     increase if you have memory problems
    Ain = Ain          # if you want to initialize with some preselected components
    #                     you can pass them here as boolean vectors
    low_rank_background = None  # None leaves background of each patch intact,
    #                             True performs global low-rank approximation 
    gnb = -2            # number of background components (rank) if positive,
    #                     else exact ring model with following settings
    #                         gnb=-2: Return background as b and W
    #                         gnb=-1: Return full rank background B
    #                         gnb= 0: Don't return background
    nb_patch = -1       # number of background components (rank) per patch,
    #                     use 0 or -1 for exact background of ring model (cf. gnb)
    min_corr = .8       # min peak value from correlation image
    min_pnr = 75        # min peak to noise ration from PNR image
    ssub_B = 1          # additional downsampling factor in space for background
    ring_size_factor = 1.4#1.4 #1.4  # radius of ring is gSiz*ring_size_factor    
    
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
    
    #Remove large or unpickable fields:
    cnm.dview=None
    cnm.b = None
    cnm.f = None
    
    #Calculate these spatial summaries of the video which we will use later to join ROIs across sessions:
    cnm.cn_filter, cnm.pnr = correlation_pnr(Y, gSig=gSig, swap_dim=False)
        
    save_object(cnm,destination)
    
    if multiprocessing:
        cm.stop_server(dview=dview) # stop it if it was running

    return(None)


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
    
    parser = argparse.ArgumentParser(description='Ca2+ extraction script.')
    parser.add_argument('input', metavar='N', type=str, nargs='+',
                       help='Pipeline input: file name or folder root name')
    parser.add_argument('--output', '-o', type=str, nargs=1,
                       help='Onput location for single file extractions; default: . ', default = '.')
    parser.add_argument('--grep', '-g', type=str, nargs = '+',
                       help='process only files with the given string in the name; default: "" ', default = "")
    parser.add_argument('-M', action="store_true",
                    help='use multiple processes')
    parser.add_argument('--overwrite',action="store_true", help='overwrite existing files')

    jobs = parser.parse_args().input
    

    job_type = get_job_type(jobs[0])
    multiprocessing = parser.parse_args().M
    overwrite = parser.parse_args().overwrite
    grep = parser.parse_args().grep
    
    print(len(jobs))
    
    if len(jobs)>1:
        output_loc=jobs[1]
    else:
        output_loc = parser.parse_args().output[0]
    

        
    if job_type=='folder':
        root = jobs[0]

        os.makedirs(os.path.join(root,'cnmfs'),exist_ok=True)
                
        files = sorted([f for f in os.listdir(os.path.join(root,'motion_corr')) if '.mmap' in f and all([(g in f) for g in grep])])
        fails = []
        for file in files:
            #try:
            name_parts = file.split('_')
            name = '_'.join(name_parts[0:2])
            bord_px = 20 #int(name_parts[4])      
            print(name,bord_px)
        
            if (not name+'_cnmf.pkl' in os.listdir(os.path.join(root,'cnmfs'))) or overwrite:
                #try:
                extract_spikes(os.path.join(root,'motion_corr',file), os.path.join(root,'cnmfs',name+'_cnmf.pkl'), bord_px=bord_px, multiprocessing=multiprocessing, Ain = None)
            #except:
            #    fails.append(file)
            #    break
            else:
                print('skipping '+name+'_cnmf.pkl')


        print('Errors while processing: '+str(fails))  

    else:
        if output_loc=='.':
            print('no output location given, saving to ./cnm.pkl')
            output_loc='./cnm.pkl'
        Ain = extract_spikes(jobs[0],output_loc,bord_px = 10, multiprocessing = parser.parse_args().M)   
        #Ain = extract_spikes(jobs[0],output_loc,bord_px = 0, multiprocessing = parser.parse_args().M, Ain = Ain)            
        

# /scratch/stiesmeyer/data  -M
