#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 25 11:24:18 2018

@author: sebastian
"""

# ['condition', 'session', 'mouse', 'date', 'timestamp', 'is_test?', 'trial', 'day', 'OL_1', 'OL_2', 'comment']

import pandas
import argparse
import os

def get_job_type(job):
    extension = [e for e in job.split('.')]
    if len(extension)==1:
        return 'folder'
    elif extension[-1]=='xlsx':
        return 'xlsx'
    elif extension[-1]=='raw':
        return 'raw'
    elif extension[-1]=='tif':
        return 'tif'
    elif extension[-1]=='mmap':
        return 'mmap'
    else:
        print("Unknown file extension; exiting with 0")
        exit()

def find_file(name_elements,folder,results):
    results+=[os.path.join(folder,f) for f in os.listdir(folder) if all([(s in folder+'/'+f) for s in name_elements])]
    for i in [f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder,f))]:
        results = find_file(name_elements,os.path.join(folder,i),results)
        
    return(results)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='The Radboud Neoruinformatics Calcium Imaging Pipeline.')
    parser.add_argument('name', metavar='N', type=str, nargs='+',
                       help='Pipeline input: file name, folder name or excel sheet')
    parser.add_argument('--input', '-i', type=str,
                       help='Base folder to search for raw videos for excel sheet input; default: . ', default = '.')
    parser.add_argument('--output', '-o', type=str,
                       help='Onput location; default: . ', default = '.')
    
    jobs = parser.parse_args().name
    input_loc = parser.parse_args().input
    output_loc = parser.parse_args().output
        
    for job in jobs:
        job_type = get_job_type(job)
        
        if job_type=='xlsx':   
            sheet = pandas.read_excel(job)
            for index, row in sheet.iterrows():
                
                try:
                    name_elements = [str(int(r)) for i,r in enumerate(row) if i in [2,3,4]]+['.raw']
                    files = sorted(find_file(name_elements,input_loc,[]))
                    if not files: print (name_elements)#files[-1])
                except:
                    print (name_elements)
            