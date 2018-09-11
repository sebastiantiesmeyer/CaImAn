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
import configparser

def get_configs(file = './cali.config'):
    C = configparser.ConfigParser()
    C.read(file)
    return C

c = get_configs()
ana_3 = os.path.expanduser(c['PATHS']['anaconda3'])
ana_2 = os.path.expanduser(c['PATHS']['anaconda2'])
decoder = os.path.expanduser(c['PATHS']['decoder'])

py_inscopix = os.path.join(ana_2,'envs',c['ENV_NAMES']['inscopix'],'bin/python')

def get_job_type(job):
    extension = [e for e in job.split('.')]
    if  os.path.isdir(job):
        return 'folder'
    elif extension[-1]=='xlsx':
        return 'xlsx'
    elif extension[-1]=='raw':
        return 'raw'
    else:
        print("Unknown file extension; exiting with 0")
        exit()

def find_file(name_elements,folder,results):
    results+=[os.path.join(folder,f) for f in os.listdir(folder) if all([(s in folder+'/'+f) for s in name_elements])]
    for i in [f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder,f))]:
        results = find_file(name_elements,os.path.join(folder,i),results)
        
    return(results)
    
def decode_file(inp,outp):
    cmd = ' '.join([py_inscopix,decoder,'"'+inp+'"',outp])   
    os.system(cmd)     

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='The Radboud MemDyn Calcium Imaging Pipeline.')
    parser.add_argument('name', metavar='N', type=str, nargs=1,
                    help='Pipeline input: file name, folder name or excel sheet')
    parser.add_argument('--output', '-o', type=str,
                    help='Output location; Overrides location in cali.config', default = None)
    parser.add_argument('--input', '-i', type=str,
                    help='Base folder to search for raw videos for excel sheet input; Overrides location in cali.config', default = None)

    
    job = parser.parse_args().name[0]
    
    input_loc = parser.parse_args().input 
    output_loc = parser.parse_args().output

    
    print('Using python binary at '+py_inscopix)
    
    job_type = get_job_type(job)
    
    if job_type=='xlsx':   
        
        if input_loc==None:
            input_loc=os.path.expanduser(c['ROOTS']['raw'])
        print('Using input from: ',(input_loc)) 
        
        if output_loc==None:
            output_loc=os.path.expanduser(c['ROOTS']['preprocessed'])
        print('Writing output to: ',(output_loc))        
        
        sheet = pandas.read_excel(job)
        fails = []
        job_list={}
                    
        for index, row in sheet.iterrows():
            
            try:
                name_elements = [str(int(r)) for i,r in enumerate(row) if i in [2,3,4]]+['.raw']
                files = sorted(find_file(name_elements,input_loc,[]))
                if not files: fails.append(name_elements)#files[-1])
                else: 
                    print('Decoding...')
                    inp=[f for f in files if len(f.split('-')[-1])>7][0]
                    mouse = str(row[2])
                    date = str(row[3])
                    time = str(int(row[4]))
                    rest = 'trial' if row[6] else 'rest'
                    name = '_'.join([mouse,date,time,rest])+'.tif'
                    outp=os.path.join(output_loc,mouse,date,name)
                    os.makedirs(os.path.join(output_loc,mouse,date),exist_ok=True)
                    decode_file(inp,outp)
                            
            except:
                fails.append(name_elements)
            break
        
        if fails:
            print('The following files were not found: ',fails)
            
    if job_type=='raw':                
        if output_loc==None:
            print("You have to define an output path with '-o [output]' for single file conversions :( ")
            exit()
        else:
            decode_file(job,output_loc)





