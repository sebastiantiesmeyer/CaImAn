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
from caiman.motion_correction import motion_correct_oneP_rigid, motion_correct_oneP_nonrigid


def motion_correct(file, destination, non_rigid = True):
    
    frate = 10                       # movie frame rate
    decay_time = 0.1                 # length of a typical transient in seconds
   
    # stop the cluster if one exists
    n_processes = psutil.cpu_count()//2
    print('using ' + str(n_processes) + ' processes')
    print("Stopping  cluster to avoid unnencessary use of memory....")
     
    
    # START CLUSTER
    if 'dview' in locals():
        cm.stop_server(dview=dview)
    c, dview, n_processes = cm.cluster.setup_cluster(
        backend='local', n_processes=n_processes, single_thread=False)   
    
    
    # motion correction parameters
    do_motion_correction_nonrigid = non_rigid
    do_motion_correction_rigid = not(non_rigid)  # in this case it will also save a rigid motion corrected movie
    gSig_filt = (4, 4)       # size of filter, in general gSig (see below),
    #                          change this one if algorithm does not work
    max_shifts = (6, 6)      # maximum allowed rigid shift
    splits_rig = 50          # for parallelization split the movies in  num_splits chuncks across time
    strides = (48, 48)       # start a new patch for pw-rigid motion correction every x pixels
    overlaps = (24, 24)      # overlap between pathes (size of patch strides+overlaps)
    splits_els = 20          # for parallelization split the movies in  num_splits chuncks across time
    #                          (remember that it should hold that length_movie/num_splits_to_process_rig>100)
    upsample_factor_grid = 4 # upsample factor to avoid smearing when merging patches
    max_deviation_rigid = 6  # maximum deviation allowed for patch with respect to rigid shifts
        
    if do_motion_correction_nonrigid or do_motion_correction_rigid:
        # do motion correction rigid
        mc = motion_correct_oneP_rigid(file,
                                       gSig_filt=gSig_filt,
                                       max_shifts=max_shifts,
                                       dview=dview,
                                       splits_rig=splits_rig,
                                       save_movie=not(do_motion_correction_nonrigid)
                                       )
    
        new_templ = mc.total_template_rig
    
    
        bord_px = np.ceil(np.max(np.abs(mc.shifts_rig))).astype(np.int)     #borders to eliminate from movie because of motion correction        
    
        # do motion correction nonrigid
        if do_motion_correction_nonrigid:
            mc = motion_correct_oneP_nonrigid(
                file,
                gSig_filt=gSig_filt,
                max_shifts=max_shifts,
                strides=strides,
                overlaps=overlaps,
                splits_els=splits_els,
                upsample_factor_grid=upsample_factor_grid,
                max_deviation_rigid=max_deviation_rigid,
                dview=dview,
                splits_rig=None,
                save_movie=True,  # whether to save movie in memory mapped format
                new_templ=new_templ  # template to initialize motion correction
            )
    
            bord_px = np.ceil(
                np.maximum(np.max(np.abs(mc.x_shifts_els)),
                           np.max(np.abs(mc.y_shifts_els)))).astype(np.int)
    
        # create memory mappable file in the right order on the hard drive (C order)        
            fname_new = cm.save_memmap([mc.fname_tot_els], base_name=destination,
                                       order = 'C', border_to_0=bord_px, dview=dview)
        else:
            fname_new = cm.save_memmap([mc.fname_tot_rig], base_name=destination,
                                       order = 'C', border_to_0=bord_px, dview=dview)
            
        
    try:
        cm.stop_server(dview=dview) # stop it if it was running
    except:
        print('No server running to stop... ')

    return fname_new


def get_job_type(job):
    extensions = [e for e in job.split('.')]

    if len(extensions)==1:
        return 'folder'
    elif extensions[-1]=='tif':
        return 'tif'
    else:
        print("Unknown file extension; exiting with 0")
        exit()




if __name__ == "__main__":  
    
    parser = argparse.ArgumentParser(description='Ca2+ motion corrections script.')
    parser.add_argument('input', metavar='N', type=str, nargs='+',
                       help='Pipeline input: file name or folder root name')
    parser.add_argument('--output', '-o', type=str, nargs=1,
                       help='Output location for single file correction; default: . ', default = '.')
    parser.add_argument('--grep', '-g', type=str, nargs = '+',
                       help='process only files with the given string in the name; default: "" ', default = "")
    parser.add_argument('-M', action="store_true",
                    help='use multiple processes')
    parser.add_argument('--overwrite',action="store_true", help='overwrite existing files')
    parser.add_argument('--single_trials',action="store_true", help='produce single trial memmaps')
    parser.add_argument('--non_rigid',action="store_true", help='include a non-rigid transformation step')
    

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

        os.makedirs(os.path.join(root,'motion_corr'),exist_ok=True)
                
        files = sorted([f for f in os.listdir(os.path.join(root,'preprocessed')) if '.tif' in f and all([(g in f) for g in grep])])
        fails = []
        
        if parser.parse_args().single_trials:
            jobs = [[f] for f in files]
        else:
            days = sorted(set([num.split('_')[1] for num in files]))
            jobs = [sorted([f for f in files if f.split('_')[1]==day]) for day in days ]
                
        for job in jobs:
            if parser.parse_args().single_trials:
                destination = os.path.join(root,'motion_corr','_'.join(job[0].split('_')[:3]))
            else:
                destination = os.path.join(root,'motion_corr','_'.join(job[0].split('_')[:2]))
            print(job)
            if not (any([(job[0] in f) for f in os.listdir(os.path.join(root,'preprocessed'))])) or parser.parse_args().overwrite:    
                motion_correct([os.path.join(root,'preprocessed',j) for j in job],destination=destination,non_rigid = parser.parse_args().non_rigid)
    else:
        motion_correct(input,parser.parse_args().output,non_rigid = parser.parse_args().non_rigid)
            
 
        
        
