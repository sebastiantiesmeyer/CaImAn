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
    max_shifts = (5, 5)      # maximum allowed rigid shift
    splits_rig = 10          # for parallelization split the movies in  num_splits chuncks across time
    strides = (48, 48)       # start a new patch for pw-rigid motion correction every x pixels
    overlaps = (24, 24)      # overlap between pathes (size of patch strides+overlaps)
    splits_els = 10          # for parallelization split the movies in  num_splits chuncks across time
    #                          (remember that it should hold that length_movie/num_splits_to_process_rig>100)
    upsample_factor_grid = 4 # upsample factor to avoid smearing when merging patches
    max_deviation_rigid = 3  # maximum deviation allowed for patch with respect to rigid shifts
        
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
            fname_new = cm.save_memmap([mc.fname_tot_els], base_name=extract_spikes,
                                       order = 'C', border_to_0=bord_px, dview=dview)
        else:
            fname_new = cm.save_memmap([mc.fname_tot_rig], base_name=extract_spikes,
                                       order = 'C', border_to_0=bord_px, dview=dview)

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
                    dest_name = '_'.join([mouse,day,'motion_corr'])
                    os.system('mkdir -p '+os.path.join(root,'motion_corr',mouse,day))
                    if not([f for f in os.listdir(os.path.join(root,'motion_corr',mouse,day)) if dest_name in f]):
                        dest = (os.path.join(root,'motion_corr',mouse,day,dest_name))
                        file = (os.path.join(root,'cropped',mouse,day,file))
                        motion_correct(file,dest)
    
    else:
        motion_correct([jobs[0]],output_loc)
        
    
        
        
        
