# -*- coding: utf-8 -*-

### Import required python modules
import os
import platform
from os import listdir, stat, makedirs, mkdir, walk, remove
from os.path import isdir, isfile, join, splitext, getmtime, basename, normpath, exists, expanduser, split, dirname, getsize, commonprefix
import pandas as pd
from time import strftime, localtime
from shutil import copy2
from blackfynn import Blackfynn
from configparser import ConfigParser
import threading
import numpy as np
import collections
import subprocess
import shutil
import re
import time
import gevent

### Global variables
curateprogress = ' '
curatestatus = ' '
curateprintstatus = ' '
total_dataset_size = 1
curated_dataset_size = 0

userpath = expanduser("~")
configpath = join(userpath, '.blackfynn', 'config.ini')
submitdataprogress = ' '
submitdatastatus = ' '
submitprintstatus = ' '
total_file_size = 1
uploaded_file_size = 0

### Internal functions
def open_file(file_path):
    """
    Opening folder on all platforms
    https://stackoverflow.com/questions/6631299/python-opening-a-folder-in-explorer-nautilus-mac-thingie

    Args:
        file_path: path of the folder (string)
    Action:
        Opens file explorer window to the given path
    """
    try:
        if platform.system() == "Windows":
            subprocess.Popen(r'explorer /select,' + str(file_path))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        raise e


def paths_from_template(df):
    """
    Checks if all paths in template files are in the same folder

    Args:
        df: path of the folder
    Returns:
        boolean: True or False depending on folder structure
    """
    jsonpath = df.to_dict()
    paths = []
    for key in jsonpath.keys():
        if '_description' not in key:
            for i in range(len(jsonpath[key])):
                if jsonpath[key][i] != '':
                    paths.append(jsonpath[key][i])

    base = commonprefix(paths)
    return base, paths


def template_check(base, paths):
    """
    Checks if all paths in template files are in the same folder

    Args:
        df: path of the folder
    Returns:
        boolean: True, if folder structure is consistent, else raises an error
    """
    folder_content = listdir(base)
    folder_content.append(basename(split(base)[0]))

    for p in paths:
        if p in folder_content or basename(dirname(p)) in folder_content:
            continue
        else:
            # return False # In case of an error
            raise Exception("Folder structure not consistent")
    return True # In case of no errors


def folder_structure_check(base, folder_path):
    """
    Checks if the new folder is in the same structure as the previous one

    Args:
        df: path of the folder
        folder_path: path of the folder
    Returns:
        total_size: Total size of the folder in bytes (integer)
    """
    prev_folders = [ name for name in listdir(base) if isdir(join(base, name)) ]
    new_folders = [ name for name in listdir(folder_path) if isdir(join(folder_path, name)) ]
    return all(elem in prev_folders  for elem in new_folders)


def custom_dataframe(df):
    """
    Input: Saved template of user
    Returns dataframe with essential features of each path
    """
    df.fillna('', inplace=True)
    jsonpath = df.to_dict()
    paths = []
    for key in jsonpath.keys():
        if '_description' not in key:
            for i in range(len(jsonpath[key])):
                if jsonpath[key][i] != '':
                    paths.append(jsonpath[key][i])
#     paths_shortened = []
    base = os.path.commonprefix(paths)
    new_df = pd.DataFrame(columns=['user_folder', 'file/folder', 'extension',
                                        'size', 'SPARC_folder'])

    jsonpath = df.to_dict()
    j = 0
    for key in jsonpath.keys():
        if '_description' not in key:
            for i in range(len(jsonpath[key])):
                if jsonpath[key][i] != '':
                    new_df.loc[j, 'user_folder'] = split(os.path.relpath(jsonpath[key][i], base))[0]
                    new_df.loc[j, 'file/folder'] = split(os.path.relpath(jsonpath[key][i], base))[1]
                    new_df.loc[j, 'extension'] = splitext(split(os.path.relpath(jsonpath[key][i], base))[1])[1]
                    new_df.loc[j, 'size'] = getsize(jsonpath[key][i])
                    new_df.loc[j, 'SPARC_folder'] = key
                    j += 1

    return new_df


def template_from_folder(folder_path):
    """
    Returns template upon providing a folder path
    """
    new_df_test = pd.DataFrame(columns=['user_folder', 'file/folder', 'extension',
                                        'size'])
    j = 0
    for path_ in listdir(folder_path):
        if isdir(join(folder_path, path_)):
            for sub_path in listdir(join(folder_path, path_)):
                new_df_test.loc[j, 'user_folder'] = path_
                new_df_test.loc[j, 'file/folder'] = splitext(sub_path)[0]
                new_df_test.loc[j, 'extension'] = splitext(sub_path)[1]
                new_df_test.loc[j, 'size'] = path_size(join(folder_path, path_, sub_path))
                j += 1
        else:
            new_df_test.loc[j, 'user_folder'] = ''
            new_df_test.loc[j, 'file/folder'] = splitext(path_)[0]
            new_df_test.loc[j, 'extension'] = splitext(path_)[1]
            new_df_test.loc[j, 'size'] = getsize(join(folder_path, path_))
            j += 1

    return new_df_test


def jsonpath_from_df(df, base):
    """
    Returns template upon providing a folder path
    """
    jsonpath_df = pd.DataFrame(columns=['code', 'code_description', 'derivatives', 'derivatives_description', 'docs',
                                    'docs_description', 'main', 'main_description', 'primary', 'primary_description',
                                    'protocol', 'protocol_description', 'source', 'source_description'])
    for key in df.SPARC_folder.unique():
        sub_df = df[df.SPARC_folder == key]
        j = 0
        for i in range(len(sub_df)):
            user_folder = sub_df.iloc[i]['user_folder']
            filename = sub_df.iloc[i]['file/folder'] + sub_df.iloc[i]['extension']
            jsonpath_df.loc[j, key] = join(base, user_folder, filename)
            j += 1
    jsonpath_df.fillna('', inplace=True)
    return jsonpath_df.to_dict('list')


def predict_folder(df):
    """
    Returns the most probable SPARC folder based on previous data
    """
    if len(df['SPARC_folder'].unique()) == 1:
        return df['SPARC_folder'].unique()[0]
    elif len(df['SPARC_folder'].unique()) == 0:
        return 'none'
    else:
        return 'conflict'


def name_extension(df, name, extension):
    """
    Returns the most probable SPARC folder based on previous data
    """
    sub_dataframe = df[df['file/folder'] == name]
    name_prediction = predict_folder(sub_dataframe)
    sub_dataframe = df[df['extension'] == extension]
    extension_prediction = predict_folder(sub_dataframe)
    if name_prediction == 'conflict' or extension_prediction == 'conflict':
        return 'conflict'
    if name_prediction != 'none' and extension_prediction != 'none':
        return 'conflict' if name_prediction != extension_prediction else name_prediction
    elif name_prediction != 'none' and extension_prediction == 'none':
        return name_prediction
    elif name_prediction == 'none' and extension_prediction != 'none':
        return extension_prediction
    else:
        return 'none'


def nearest_folder_size(df, target_number):
    """
    Returns the most probable folder based on size of the file
    """
    closest_previous_size = min(df.loc[:,'size'].values, key=lambda x:abs(x-target_number))
    return df[df['size'] == closest_previous_size]['SPARC_folder'].values[0]


def folder_size(path):
    """
    Provides the size of the folder indicated by path

    Args:
        path: path of the folder (string)
    Returns:
        total_size: total size of the folder in bytes (integer)
    """
    total_size = 0
    start_path = '.'  # To get size of current directory
    for path, dirs, files in walk(path):
        for f in files:
            fp = join(path, f)
            total_size += getsize(fp)
    return total_size


def dataset_size_blackfynn():
    """
    Function to get storage size of a dataset on Blackfynn
    """
    global myds
    global bf
    try:
        selected_dataset_id = myds.id
        bf_response = bf._api._get('/datasets/' + str(selected_dataset_id))
        return bf_response['storage'] if 'storage' in bf_response.keys() else 0
    except Exception as e:
        raise e


def path_size(path):
    """
    Returns size of the path, after checking if it's a folder or a file
    Args:
        path: path of the file/folder (string)
    Returns:
        total_size: total size of the file/folder in bytes (integer)
    """
    if isdir(path):
        return folder_size(path)
    else:
        return getsize(path)


def create_folder_level_manifest(datasetpath, jsonpath, jsondescription):
    """
    Function to create manifest files for each SPARC folder.
    Files are created in a temporary folder

    Args:
        datasetpath: path of the dataset (string)
        jsonpath: all paths in json format with key being SPARC folder names (dictionary)
        jsondescription: description associated with each path (dictionary)
    Action:
        Creates manifest files in csv format for each SPARC folder
    """
    global total_dataset_size
    try:
        folders = list(jsonpath.keys())
        if 'main' in folders:
            folders.remove('main')
        # In each SPARC folder, generate a manifest file
        for folder in folders:
            if (jsonpath[folder] != []):
                # Initialize dataframe where manifest info will be stored
                df = pd.DataFrame(columns=['filename', 'timestamp', 'description',
                                        'file type', 'Additional Metadata'])
                # Get list of files/folders in the the folde#
                # Remove manifest file from the list if already exists
                folderpath = join(datasetpath, folder)
                allfiles = jsonpath[folder]
                alldescription = jsondescription[folder + '_description']
                manifestexists = join(folderpath, 'manifest.csv')

                countpath = -1
                for pathname in allfiles:
                    countpath += 1
                    if basename(pathname) == 'manifest.csv' or basename(pathname) == 'manifest.xlsx':
                        allfiles.pop(countpath)
                        alldescription.pop(countpath)

                # Populate manifest dataframe
                filename, timestamp, filetype, filedescription = [], [], [], []
                countpath = -1
                for paths in allfiles:
                    if isdir(paths):
                        key = basename(paths)
                        alldescription.pop(0)
                        for subdir, dirs, files in os.walk(paths):
                            for file in files:
                                filepath = join(paths,subdir,file) #full local file path
                                lastmodtime = getmtime(filepath)
                                timestamp.append(strftime('%Y-%m-%d %H:%M:%S',
                                                                      localtime(lastmodtime)))
                                fullfilename = basename(filepath)
                                if folder == 'main': # if file in main folder
                                    filename.append(fullfilename) if folder == '' else filename.append(join(folder, fullfilename))
                                else:
                                    subdirname = os.path.relpath(subdir, paths) # gives relative path of the directory of the file w.r.t paths
                                    if subdirname == '.':
                                        filename.append(join(key, fullfilename))
                                    else:
                                        filename.append(join(key, subdirname, fullfilename))

                                fileextension = splitext(fullfilename)[1]
                                if not fileextension:  # if empty (happens e.g. with Readme files)
                                    fileextension = 'None'
                                filetype.append(fileextension)
                                filedescription.append('')
                    else:
                        countpath += 1
                        file = basename(paths)
                        filename.append(file)
                        lastmodtime = getmtime(paths)
                        timestamp.append(strftime('%Y-%m-%d %H:%M:%S',
                                                  localtime(lastmodtime)))
                        filedescription.append(alldescription[countpath])
                        if isdir(paths):
                            filetype.append('folder')
                        else:
                            fileextension = splitext(file)[1]
                            if not fileextension:  #if empty (happens e.g. with Readme files)
                                fileextension = 'None'
                            filetype.append(fileextension)

                df['filename'] = filename
                df['timestamp'] = timestamp
                df['file type'] = filetype
                df['description'] = filedescription

                makedirs(folderpath)
                # Save manifest as Excel sheet
                manifestfile = join(folderpath, 'manifest.csv')
                df.to_csv(manifestfile, index=None, header=True)
                total_dataset_size += path_size(manifestfile)
                jsonpath[folder].append(manifestfile)

        return jsonpath

    except Exception as e:
        raise e


def check_forbidden_characters(my_string):
    """
    Check for forbidden characters in file/folder name

    Args:
        my_string: string with characters (string)
    Returns:
        False: no forbidden character
        True: presence of forbidden character(s)
    """
    regex = re.compile('[@!#$%^&*()<>?/\|}{~:],')
    if(regex.search(my_string) == None):
        return False
    else:
        return True


def return_new_path(topath):
    """
    This function checks if a folder already exists and in such cases,
    appends (2) or (3) etc. to the folder name

    Args:
        topath: path where the folder is supposed to be created (string)
    Returns:
        topath: new folder name based on the availability in destination folder (string)
    """
    if exists(topath):
        i = 2
        while True:
            if not exists(topath + ' (' + str(i) + ')'):
                return topath + ' (' + str(i) + ')'
            i += 1
    else:
        return topath


def mycopyfileobj(fsrc, fdst, length=16*1024*16):
    """
    Helper function to copy file

    Args:
        fsrc: source file opened in python (file-like object)
        fdst: destination file accessed in python (file-like object)
        length: copied buffer size in bytes (integer)
    """
    global curateprogress
    global total_dataset_size
    global curated_dataset_size
    while True:
        buf = fsrc.read(length)
        if not buf:
            break
        gevent.sleep(0)
        fdst.write(buf)
        curated_dataset_size += len(buf)

def mycopyfile_with_metadata(src, dst, *, follow_symlinks=True):
    """
    Copy file src to dst with metadata (timestamp, permission, etc.) conserved

    Args:
        src: source file (string)
        dst: destination file (string)
    Returns:
        dst
    """
    if not follow_symlinks and os.path.islink(src):
        os.symlink(os.readlink(src), dst)
    else:
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                mycopyfileobj(fsrc, fdst)
    shutil.copystat(src, dst)
    return dst


### Prepare dataset
def save_file_organization(jsonpath, jsondescription, pathsavefileorganization):
    """
    Associated with 'Save' button in the SODA interface
    Saves the paths and associated descriptions from the interface table to a CSV file for future use
    Each json key (SPARC foler name) becomes a header in the CSV

    Args:
        jsonpath: paths of all files (dictionary)
        jsondescription: description associated with each file (dictionary)
        pathsavefileorganization: destination path for CSV file to be saved (string)
    Action:
        Creates CSV file with path and description for files in SPARC folders
    """
    try:
        mydict = jsonpath
        mydict2 = jsondescription
        mydict.update(mydict2)
        dictkeys = list(mydict.keys())
        dictkeys.sort()
        df = pd.DataFrame(columns=[dictkeys[0]])
        df[dictkeys[0]] = mydict[dictkeys[0]]
        for i in range(1,len(dictkeys)):
            dfnew = pd.DataFrame(columns=[dictkeys[i]])
            dfnew[dictkeys[i]] = mydict[dictkeys[i]]
            df = pd.concat([df, dfnew], axis=1)
        df = df.replace(np.nan, '', regex=True)
        csvsavepath = join(pathsavefileorganization)
        df.to_csv(csvsavepath, index = None, header=True)
        return 'Saved!'
    except Exception as e:
        raise e


def import_file_organization(pathuploadfileorganization, headernames):
    """
    Associated with 'Import' button in the SODA interface
    Import previously saved progress (CSV file) for viewing in the SODA interface

    Args:
        pathuploadfileorganization: path of previously saved CSV file (string)
        headernames: names of SPARC folder (list of strings)
    Returns:
        mydict: dictionary with headers of CSV file as keys and cell contents as list of strings for each key
    """
    try:
        csvsavepath = join(pathuploadfileorganization)
        df = pd.read_csv(csvsavepath)
        dfnan = df.isnull()
        mydict = {}
        dictkeys = df.columns
        compare = lambda x, y: collections.Counter(x) == collections.Counter(y)
        if not compare(dictkeys, headernames):
            raise Exception("Error: Please select a valid file")
        rowcount = len(df.index)
        for i in range(len(dictkeys)):
            pathvect = []
            for j in range(rowcount):
                pathval = df.at[j, dictkeys[i]]
                if not dfnan.at[j, dictkeys[i]]:
                    pathvect.append(pathval)
                else:
                    pathvect.append("")
            mydict[dictkeys[i]] = pathvect
        return mydict
    except Exception as e:
        raise e


def create_preview_files(paths, folder_path):
    """
    Creates folders and empty files from original 'paths' to the destination 'folder_path'

    Args:
        paths: paths of all the files that need to be copied (list of strings)
        folder_path: Destination to which the files / folders need to be copied (string)
    Action:
        Creates folders and empty files at the given 'folder_path'
    """
    for p in paths:
        gevent.sleep(0)
        if isfile(p):
            file = basename(p)
            open(join(folder_path, file), 'a').close()
        else:
            all_files = listdir(p)
            all_files_path = []
            for f in all_files:
                all_files_path.append(join(p, f))

            pname = basename(p)
            new_folder_path = join(folder_path, pname)
            makedirs(new_folder_path)
            create_preview_files(all_files_path, new_folder_path)
    return


def preview_file_organization(jsonpath):
    """
    Associated with 'Preview' button in the SODA interface
    Creates a folder for preview and adds mock files from SODA table (same name as origin but 0 kb in size)
    Opens the dialog box to showcase the files / folders added

    Args:
        jsonpath: dictionary containing all paths (keys are SPARC folder names)
    Action:
        Opens the dialog box at preview_path
    Returns:
        preview_path: path of the folder where the preview files are located
    """
    mydict = jsonpath
    userpath = expanduser("~")
    preview_path = join(userpath, "SODA", "Preview")
    try:
        if isdir(preview_path):
            delete_preview_file_organization()
            makedirs(preview_path)
        else:
            makedirs(preview_path)
    except Exception as e:
        raise e

    try:
        folderrequired = []
        for i in mydict.keys():
            if mydict[i] != []:
                folderrequired.append(i)
                if i != 'main':
                    makedirs(join(preview_path, i))

        for i in folderrequired:
            paths = mydict[i]
            if (i == 'main'):
                create_preview_files(paths, join(preview_path))
            else:
                create_preview_files(paths, join(preview_path, i))
        open_file(preview_path)
        return preview_path
    except Exception as e:
        raise e


def delete_preview_file_organization():
    """
    Associated with 'Delete Preview Folder' button of the SODA interface

    Action:
        Deletes the 'Preview' folder from the disk
    """
    try:
        userpath = expanduser("~")
        preview_path = join(userpath, "SODA")
        if isdir(preview_path):
            shutil.rmtree(preview_path, ignore_errors=True)
        else:
            raise Exception("Error: Preview folder not present or already deleted!")
    except Exception as e:
        raise e


def smart_organize(template_path, folder_path):
    """

    Input:
        template_path: Path of template file (CSV)
        folder_path: Path of new dataset
    Returns:
        jsonpath:
        unsure_files:
    """
    template_path, folder_path = template_path[0], folder_path[0]
    df = pd.read_csv(template_path)
    df.fillna('', inplace=True)
    base, paths = paths_from_template(df)
    if template_check(base, paths): # Check for validity of template file paths
        new_df = custom_dataframe(df) # Creating custom dataframe to ease decision making process
    if folder_structure_check(base, folder_path): # Check for validity of new folder's structure
        new_df_test = template_from_folder(folder_path)
    else:
        raise Exception("Folder structure not consistent with the old folder structure")

    # Hard-coded logic
    new_df_test['SPARC_folder'] = ''
    unsure_files = []
    for i in range(len(new_df_test)):
        # Variables for the test set
        old_folder = new_df_test.loc[i, 'user_folder']
        old_extension = new_df_test.loc[i, 'extension']
        path_name = new_df_test.loc[i, 'file/folder']
        full_name = path_name + old_extension

        folder_dataframe = new_df[new_df.user_folder == old_folder]
        if predict_folder(folder_dataframe) == 'none':
            unsure_files.append(join(new_df_test.loc[i, 'user_folder'], new_df_test.loc[i, 'file/folder']))
        elif predict_folder(folder_dataframe) != 'conflict':
            new_df_test.loc[i, 'SPARC_folder'] = predict_folder(folder_dataframe)
        else:
            # Checking for name + extension
            sub_dataframe = folder_dataframe[(folder_dataframe['file/folder'] == path_name) & (folder_dataframe['extension'] == old_extension)]
            if predict_folder(sub_dataframe) != 'conflict' and predict_folder(sub_dataframe) != 'none':
                new_df_test.loc[i, 'SPARC_folder'] = predict_folder(sub_dataframe)
            elif predict_folder(sub_dataframe) == 'conflict':
                unsure_files.append(join(new_df_test.loc[i, 'user_folder'], new_df_test.loc[i, 'file/folder']))
            else:
                # Checking for name and extension separately
                if name_extension(folder_dataframe, path_name, old_extension) != 'conflict' and name_extension(folder_dataframe, path_name, old_extension) != 'none':
                    new_df_test.loc[i, 'SPARC_folder'] = name_extension(folder_dataframe, path_name, old_extension)
                elif name_extension(new_df, path_name, old_extension) == 'none':
                    unsure_files.append(join(new_df_test.loc[i, 'user_folder'], new_df_test.loc[i, 'file/folder']))
                else:
                    # Predicting most probable SPARC folder based on file size
                    new_df_test.loc[i, 'SPARC_folder'] = nearest_folder_size(new_df, new_df_test.loc[i, 'size'])

    return (jsonpath_from_df(new_df_test, folder_path), ','.join(str(e) for e in unsure_files))


def create_dataset(jsonpath, pathdataset):
    """
    Associated with 'Create new dataset locally' option of SODA interface
    for creating requested folders and files to the destination path specified

    Args:
        jsonpath: all paths (dictionary, keys are SPARC folder names)
        pathdataset: destination path for creating a new dataset as specified (string)
    Action:
        Creates the folders and files specified
    """
    global curateprogress
    try:
        mydict = jsonpath
        folderrequired = []

        #create SPARC folder structure
        for i in mydict.keys():
            if mydict[i] != []:
                folderrequired.append(i)
                if i != 'main':
                    makedirs(join(pathdataset, i))

        # create all subfolders and generate a list of all files to copy
        listallfiles = []
        for i in folderrequired:
            if i == 'main':
                outputpath = pathdataset
            else:
                outputpath = join(pathdataset, i)
            for tablepath in mydict[i]:
                if isdir(tablepath):
                    foldername = basename(tablepath)
                    outputpathdir = join(outputpath, foldername)
                    if not os.path.isdir(outputpathdir):
                        os.mkdir(outputpathdir)
                    for dirpath, dirnames, filenames in os.walk(tablepath):
                        distdir = os.path.join(outputpathdir, os.path.relpath(dirpath, tablepath))
                        if not os.path.isdir(distdir):
                            os.mkdir(distdir)
                        for file in filenames:
                            srcfile = os.path.join(dirpath, file)
                            distfile = os.path.join(distdir, file)
                            listallfiles.append([srcfile, distfile])
                else:
                    srcfile = tablepath
                    file = basename(tablepath)
                    distfile= os.path.join(outputpath, file)
                    listallfiles.append([srcfile, distfile])

        # copy all files to corresponding folders
        for fileinfo in listallfiles:
            srcfile = fileinfo[0]
            distfile = fileinfo[1]
            curateprogress = 'Copying ' + str(srcfile)
            mycopyfile_with_metadata(srcfile, distfile)

    except Exception as e:
        raise e


def curate_dataset(sourcedataset, destinationdataset, pathdataset, newdatasetname,\
        submissionstatus, pathsubmission, datasetdescriptionstatus, pathdescription, \
        subjectsstatus, pathsubjects, samplesstatus, pathsamples, manifeststatus, \
        jsonpath, jsondescription):
    """
    Associated with 'Generate' button in the 'Generate dataset' section of SODA interface
    Checks validity of files / paths / folders and then generates the files and folders
    as requested along with progress status

    Args:
        sourcedataset: state of the source dataset ('already organized' or 'not organized')
        destinationdataset: type of destination dataset ('modify existing', 'create new', or 'upload to blackfynn')
        pathdataset: destination path of new dataset if created locally or name of blackfynn account (string)
        newdatasetname: name of the local dataset or name of the dataset on blackfynn (string)
        submissionstatus: boolean to check if user request submission file
        pathsubmission: path to the submission file (string)
        datasetdescriptionstatus: boolean to check if user request dataset_description file
        pathdescription: path to the dataset_description file (string)
        subjectsstatus: boolean to check if user request subjects file
        pathsubjects: path to the subjects file (string)
        samplesstatus: boolean to check if user request samples file
        pathsamples: path to the ssamples file (string)
        manifeststatus: boolean to check if user request manifest files
        jsonpath: path of the files to be included in the dataset (dictionary)
        jsondescription: associated description to be included in manifest file (dictionary)
    """
    global curatestatus #set to 'Done' when completed or error to stop progress tracking from front-end
    global curateprogress #GUI messages shown to user to provide update on progress
    global curateprintstatus # If = "Curating" Progress messages are shown to user
    global total_dataset_size # total size of the dataset to be generated
    global curated_dataset_size # total size of the dataset generated (locally or on blackfynn) at a given time
    global start_time

    curateprogress = ' '
    curatestatus = ''
    curateprintstatus = ' '
    error, c = '', 0
    curated_dataset_size = 0
    start_time = 0

    # if sourcedataset == 'already organized':
    #     if not isdir(pathdataset):
    #         curatestatus = 'Done'
    #         raise Exception('Error: Please select a valid dataset folder')

    if destinationdataset == 'create new':
        if not isdir(pathdataset):
            curatestatus = 'Done'
            raise Exception('Error: Please select a valid folder for new dataset')
        if (check_forbidden_characters(newdatasetname) or not newdatasetname):
            curatestatus = 'Done'
            raise Exception('Error: Please enter a valid name for new dataset folder')

    error, c = '', 0
    if submissionstatus:
        if not isfile(pathsubmission):
            curatestatus = 'Done'
            error = error + 'Error: Select valid path for submission file<br>'
            c += 1
        # Adding check for correct file name
        elif splitext(basename(pathsubmission))[0] != 'submission':
            curatestatus = 'Done'
            error = error + 'Error: Select valid name for submission file<br>'
            c += 1

    if datasetdescriptionstatus:
        if not isfile(pathdescription):
            curatestatus = 'Done'
            error = error + 'Error: Select valid path for dataset description file<br>'
            c += 1
        # Adding check for correct file name
        elif splitext(basename(pathdescription))[0] != 'dataset_description':
            curatestatus = 'Done'
            error = error + 'Error: Select valid name for dataset_description file<br>'
            c += 1

    if subjectsstatus:
        if not isfile(pathsubjects):
            curatestatus = 'Done'
            error = error + 'Error: Select valid path for subjects file<br>'
            c += 1
        # Adding check for correct file name
        elif splitext(basename(pathsubjects))[0] != 'subjects':
            curatestatus = 'Done'
            error = error + 'Error: Select valid name for subjects file<br>'
            c += 1

    if samplesstatus:
        if not isfile(pathsamples):
            curatestatus = 'Done'
            error = error + 'Error: Select valid path for samples file<br>'
            c += 1
        # Adding check for correct file name
        elif splitext(basename(pathsamples))[0] != 'samples':
            curatestatus = 'Done'
            error = error + 'Error: Select valid name for samples file<br>'
            c += 1
    if c > 0:
        raise Exception(error)

    # check if path in jsonpath are valid and calculate total dataset size
    error, c = '', 0
    total_dataset_size = 0
    for folders in jsonpath.keys():
        if jsonpath[folders] != []:
            for path in jsonpath[folders]:
                if exists(path):
                    total_dataset_size += path_size(path)
                else:
                    c += 1
                    error = error + path + ' does not exist <br>'

    if c > 0:
        error = error + '<br>Please remove invalid paths'
        curatestatus = 'Done'
        raise Exception(error)

    # Add metadata to jsonpath
    userpath = expanduser("~")
    metadatapath = join(userpath, 'SODA_metadata')
    curateprogress = 'Generating metadata'
    if manifeststatus:
        # Creating folder to store manifest file
        try:
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
            makedirs(metadatapath)
            jsonpath = create_folder_level_manifest(metadatapath, jsonpath, jsondescription)
        except Exception as e:
            curatestatus = 'Done'
            raise e

    if submissionstatus:
        jsonpath['main'].append(pathsubmission)
        total_dataset_size += path_size(pathsubmission)

    if datasetdescriptionstatus:
        jsonpath['main'].append(pathdescription)
        total_dataset_size += path_size(pathdescription)

    if subjectsstatus:
        jsonpath['main'].append(pathsubjects)
        total_dataset_size += path_size(pathsubjects)

    if samplesstatus:
        jsonpath['main'].append(pathsamples)
        total_dataset_size += path_size(pathsamples)

    # MODIFY EXISTING
    if destinationdataset == 'modify existing':
        error, c = '', 0
        namefiles = [f for f in listdir(pathdataset) if isfile(join(pathdataset, f))]
        if ('submission.xlsx' in namefiles or 'submission.csv' in namefiles) and submissionstatus:
            error = error + 'submission file already present<br>'
            c += 1
        if ('dataset_description.xlsx' in namefiles or 'dataset_description.csv' in namefiles) and datasetdescriptionstatus:
            error = error + 'dataset_description file already present<br>'
            c += 1
        if  ('samples.xlsx' in namefiles or 'samples.csv' in namefiles) and samplesstatus:
            error = error + 'samples file already present<br>'
            c += 1
        if  ('subjects.xlsx' in namefiles or 'subjects.csv' in namefiles) and subjectsstatus:
            error = error + 'subjects file already present<br>'
            c += 1

        if c > 0:
            error = error + '<br>Error: Either delete or select "None" in the SODA interface'
            curatestatus = 'Done'
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
            raise Exception(error)

        # If no errors, code-block below will execute which will start the data generation process
        else:
            try:
                open_file(pathdataset)
                curateprogress = 'Started'
                start_time = time.time()
                curateprintstatus = 'Curating'
                curateprogress = "New dataset not requested"

                metadata_files = ['submission', 'dataset_description', 'samples', 'subjects']
                for filepath in jsonpath['main']:
                    if splitext(basename(filepath))[0] in metadata_files:
                        copy2(filepath, pathdataset)

                if manifeststatus:
                    for folder in jsonpath.keys():
                        if folder != 'main':
                            for filepath in jsonpath[folder]:
                                if splitext(basename(filepath))[0] == 'manifest':
                                    copy2(filepath, join(pathdataset, folder))

                    curateprogress = 'Manifest created'

                curateprogress = 'Success: COMPLETED!'
                curatestatus = 'Done'
                shutil.rmtree(metadatapath) if isdir(metadatapath) else 0

            except Exception as e:
                curatestatus = 'Done'
                shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
                raise e

    # CREATE NEW
    elif destinationdataset == 'create new':
        try:
            pathnewdatasetfolder = join(pathdataset, newdatasetname)
            pathnewdatasetfolder  = return_new_path(pathnewdatasetfolder)
            open_file(pathnewdatasetfolder)

            curateprogress = 'Started'
            curateprintstatus = 'Curating'
            start_time = time.time()

            pathdataset = pathnewdatasetfolder
            mkdir(pathdataset)
            create_dataset(jsonpath, pathdataset)

            curateprogress = 'New dataset created'
            curateprogress = 'Success: COMPLETED!'
            curatestatus = 'Done'
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0

        except Exception as e:
            curatestatus = 'Done'
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
            raise e

    # UPLOAD TO BLACKFYNN
    elif destinationdataset == 'upload to blackfynn':
        error, c = '', 0
        accountname = pathdataset
        bfdataset = newdatasetname

        try:
            bf = Blackfynn(accountname)
        except Exception as e:
            curatestatus = 'Done'
            error = error + 'Error: Please select a valid Blackfynn account<br>'
            c += 1

        try:
            myds = bf.get_dataset(bfdataset)
        except Exception as e:
            curatestatus = 'Done'
            error = error + 'Error: Please select a valid Blackfynn dataset<br>'
            c += 1

        if c>0:
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
            raise Exception(error)

        try:
            selected_dataset_id = myds.id
            dataset_permission_info = bf._api._get('/datasets/' + str(selected_dataset_id) + '/permission')
            role = dataset_permission_info['permission']
            if role in ['viewer', 'delete']:
                curatestatus = 'Done'
                error = "Error: You have 'viewer' permission only for the selected dataset"
                raise Exception(error)
        except Exception as e:
            raise e

        try:
            def calluploaddirectly():
                global curateprogress
                global curatestatus
                curateprogress = "Started uploading to dataset %s" %(bfdataset)
                # return submitdataprogress
                myds = bf.get_dataset(bfdataset)
                myfolder = myds.name
                for folder in jsonpath.keys():
                    if jsonpath[folder] != []:
                        if folder != 'main':
                            mybffolder = myds.create_collection(folder)
                        else:
                            mybffolder = myds
                        for mypath in jsonpath[folder]:
                            if isdir(mypath):
                                temp_bffolder = mybffolder
                                mybffolder = mybffolder.create_collection(basename(mypath))
                                curateprogress = str(mypath)
                                directly_upload_structured_file(mybffolder, mypath, folder)
                                mybffolder = temp_bffolder
                            else:
                                curateprogress = str(mypath)
                                directly_upload_structured_file(mybffolder, mypath, folder)

                curateprogress = 'Success: COMPLETED!'
                curatestatus = 'Done'
                shutil.rmtree(metadatapath) if isdir(metadatapath) else 0

            curateprintstatus = 'Curating'
            start_time = time.time()
            t = threading.Thread(target=calluploaddirectly)
            t.start()
        except Exception as e:
            curatestatus = 'Done'
            shutil.rmtree(metadatapath) if isdir(metadatapath) else 0
            raise e

def directly_upload_structured_file(myds, mypath, myfolder):
    """
    Helper function to upload given folder to Blackfynn dataset in the original folder structure

    Args:
        myds: Dataset name on Blackfynn (string)
        mypath: Path of the organized dataset on local machine (string)
        myfolder: Current subfolder inside the path (string)
    Action:
        Uploads the files/folders to Blackfynn
    """
    global curateprogress
    global curated_dataset_size
    global total_dataset_size

    try:
        mypath = join(mypath)
        if isdir(mypath):
            for f in listdir(mypath):
                if isfile(join(mypath, f)):
                    filepath = join(mypath, f)
                    curateprogress =  "Uploading " + filepath
                    myds.upload(filepath, use_agent=False)
                    curated_dataset_size += getsize(filepath)
                else:
                    mybffolder = myds.create_collection(f)
                    myfolderpath = join(mypath, f)
                    directly_upload_structured_file(mybffolder, myfolderpath, f)
        else:
            curateprogress = "Uploading " + str(mypath)
            myds.upload(mypath, use_agent=False)
            curated_dataset_size += getsize(mypath)

    except Exception as e:
        curatestatus = 'Done'
        raise e


def curate_dataset_progress():
    """
    Function frequently called by front end to help keep track of the dataset generation progress
    """
    global curateprogress
    global curatestatus
    global curateprintstatus
    global total_dataset_size
    global curated_dataset_size
    global start_time
    elapsed_time = time.time() - start_time
    return (curateprogress, curatestatus, curateprintstatus, total_dataset_size, curated_dataset_size, elapsed_time/60)


### Manage datasets (Blackfynn interface)
def bf_add_account(keyname, key, secret):
    """
    Associated with 'Add account' button in 'Login to your Blackfynn account' section of SODA

    Args:
        keyname: Name of the account to be associated with the given credentials (string)
        key: API key (string)
        secret: API Secret (string)
    Action:
        Adds account to the Blackfynn configuration file (local machine)
    """
    try:
        error, c = '', 0
        keyname = keyname.strip()
        if (not keyname) or (not key) or (not secret):
            raise Exception('Error: Please enter valid keyname, key, and/or secret')

        if (keyname.isspace()) or (key.isspace()) or (secret.isspace()):
            raise Exception('Error: Please enter valid keyname, key, and/or secret')

        bfpath = join(userpath, '.blackfynn')
        # Load existing or create new config file
        config = ConfigParser()
        if exists(configpath):
            config.read(configpath)
            if config.has_section(keyname):
                raise Exception('Error: Key name already exists')
        else:
            if not exists(bfpath):
                mkdir(bfpath)
            if not exists(join(bfpath, 'cache')):
                mkdir(join(bfpath, 'cache'))

        # Add new account
        config.add_section(keyname)
        config.set(keyname, 'api_token', key)
        config.set(keyname, 'api_secret', secret)

        with open(configpath, 'w') as configfile:
            config.write(configfile)

    except Exception as e:
        raise e

    # Check key and secret are valid, if not delete account from config
    try:
        bf = Blackfynn(keyname)
        with open(configpath, 'w') as configfile:
            config.write(configfile)
        return 'Success: added account ' + str(bf)
    except:
        bf_delete_account(keyname)
        raise Exception('Authentication Error: please check that key name, key, and secret are entered properly')


def bf_delete_account(keyname):
    """
    Args:
        keyname: name of local Blackfynn account key (string)
    Action:
        Deletes account information from the Blackfynn config file
    """
    config = ConfigParser()
    config.read(configpath)
    config.remove_section(keyname)
    with open(configpath, 'w') as configfile:
        config.write(configfile)


def bf_account_list():
    """
    Action:
        Returns list of accounts stored in the system
    """
    try:
        accountlist = ['Select']
        if exists(configpath):
            config = ConfigParser()
            config.read(configpath)
            accountname = config.sections()
            accountnamenoglobal = [n for n in accountname if n != "global"]
            if accountnamenoglobal:
                for n in accountnamenoglobal:
                    try:
                        bfn = Blackfynn(n)
                        accountlist.append(n)
                    except:
                        config.remove_section(n)
                with open(configpath, 'w') as configfile:
                    config.write(configfile)
        return accountlist

    except Exception as e:
        raise e


def bf_dataset_account(accountname):
    """
    Args:
        accountname: name of local Blackfynn account key (string)
    Return:
        dataset_list: list of datasets associated with the specified account Name (list of string)
    Action:
        Returns list of datasets associated with the specified account Name ('accountname')
    """
    try:
        dataset_list = []
        bf = Blackfynn(accountname)
        current_user = bf._api._get('/user')
        current_user_id = current_user['id']
        for ds in bf.datasets():
            dataset_list.append(ds.name)
        dataset_list.sort(key=lambda v: v.upper()) # Returning the list of datasets in alphabetical order
        dataset_list.insert(0, ['Select dataset'])
        return dataset_list
    except Exception as e:
        raise e


def bf_account_details(accountname):
    """
    Args:
        accountname: name of local Blackfynn account key (string)
    Return:
        acc_details: account user email and organization (string)
    Action:
        Returns: return details of user associated with the account
    """
    try:
        bf = Blackfynn(accountname)
        acc_details = "User email: " + bf.profile.email + "<br>"
        acc_details = acc_details + "Organization: " + bf.context.name
        return acc_details
    except Exception as e:
        raise e


def bf_new_dataset_folder(datasetname, accountname):
    """
    Associated with 'Create' button in 'Create new dataset folder'

    Args:
        datasetname: name of the dataset to be created (string)
        accountname: account in which the dataset needs to be created (string)
    Action:
        Creates dataset for the account specified
    """
    try:
        error, c = '', 0
        datasetname = datasetname.strip()

        if check_forbidden_characters(datasetname):
            error = error + 'Error: Please enter valid dataset name' + '\n'
            c += 1

        if (not datasetname):
            error = error + 'Error: Please enter valid dataset name' + '\n'
            c += 1

        if (datasetname.isspace()):
            error = error + 'Error: Please enter valid dataset name' + '\n'
            c += 1

        try:
            bf = Blackfynn(accountname)
        except Exception as e:
            error = error + 'Error: Please select a valid Blackfynn account' + '\n'
            c += 1

        if c>0:
            raise Exception(error)

        dataset_list = []
        for ds in bf.datasets():
            dataset_list.append(ds.name)
        if datasetname in dataset_list:
            raise Exception('Error: Dataset name already exists')
        else:
            bf.create_dataset(datasetname)

    except Exception as e:
        raise e


def upload_structured_file(myds, mypath, myfolder):
    """
    Helper function to upload given folder to Blackfynn dataset in the original folder structure

    Input:
        myds: dataset name on Blackfynn (string)
        mypath: path of the organized dataset on local machine (string)
        myfolder: current folder inside the path (string)
    Action:
        Uploads the folder to Blackfynn
    """
    global submitdataprogress
    global submitdatastatus
    global uploaded_file_size

    try:
        mypath = join(mypath)
        for f in listdir(mypath):
            if isfile(join(mypath, f)):
                filepath = join(mypath, f)
                submitdataprogress =  "Uploading " + str(filepath)
                myds.upload(filepath, use_agent=False)
                uploaded_file_size += getsize(filepath)
            else:
                submitdataprogress = "Creating folder " + f
                mybffolder = myds.create_collection(f)
                myfolderpath = join(mypath, f)
                upload_structured_file(mybffolder, myfolderpath, f)

    except Exception as e:
        raise e


def bf_submit_dataset(accountname, bfdataset, pathdataset):
    """
    Associated with 'Submit dataset' button in 'Submit new dataset' section
    Uploads the specified folder to the specified dataset on Blackfynn account

    Input:
        accountname: account in which the dataset needs to be created (string)
        bfdataset: name of the dataset on Blackfynn (string)
        pathdataset: path of dataset on local machine (string)
    Action:
        Uploads dataset on Blackfynn account
    """
    global submitdataprogress
    global submitdatastatus
    global total_file_size
    global uploaded_file_size
    global submitprintstatus

    total_file_size = folder_size(pathdataset)
    submitdataprogress = ' '
    submitdatastatus = ' '
    uploaded_file_size = 0
    submitprintstatus = ' '
    error, c = '', 0

    try:
        bf = Blackfynn(accountname)
    except Exception as e:
        submitdatastatus = 'Done'
        error = error + 'Error: Please select a valid Blackfynn account'
        raise Exception(error)

    try:
        myds = bf.get_dataset(bfdataset)
    except Exception as e:
        submitdatastatus = 'Done'
        error = error + 'Error: Please select a valid Blackfynn dataset' + '<br>'
        c += 1

    if not isdir(pathdataset):
        submitdatastatus = 'Done'
        error = error + 'Error: Please select a valid local dataset folder' + '<br>'
        c += 1
    if c>0:
        raise Exception(error)

    try:
        selected_dataset_id = myds.id
        dataset_permission_info = bf._api._get('/datasets/' + str(selected_dataset_id) + '/permission')
        role = dataset_permission_info['permission']
        if role in ['viewer', 'delete']:
            submitdatastatus = 'Done'
            error = "Error: You have 'viewer' permission only for the selected dataset"
            raise Exception(error)
    except Exception as e:
        raise e

    try:
        def calluploadfolder():
            global submitdataprogress
            global submitdatastatus
            # global initial_bfdataset_size
            submitdataprogress = "Started uploading to dataset %s \n" %(bfdataset)
            myds = bf.get_dataset(bfdataset)
            myfolder = myds.name
            # initial_bfdataset_size = dataset_size_blackfynn()
            mypath = pathdataset
            upload_structured_file(myds, mypath, myfolder)
            submitdataprogress = submitdataprogress + ', ,' + "Success: dataset and associated files have been uploaded"
            submitdatastatus = 'Done'

        submitprintstatus = 'Uploading'
        t = threading.Thread(target=calluploadfolder)
        t.start()
    except Exception as e:
        submitdatastatus = 'Done'
        raise e


def submit_dataset_progress():
    """
    Keeps track of the dataset submission progress
    """
    global submitdataprogress
    global submitdatastatus
    global submitprintstatus
    global uploaded_file_size
    global total_file_size
    return (submitdataprogress, submitdatastatus, submitprintstatus, uploaded_file_size, total_file_size)


def bf_get_users(selected_bfaccount):
    """
    Function to get list of users belonging to the organization of
    the given Blackfynn account

    Args:
      selected_bfaccount: name of selected Blackfynn acccount (string)
    Retun:
        list_users : list of users (first name -- last name) associated with the organization of the
        selected Blackfynn account (list of string)
    """
    try:
        bf = Blackfynn(selected_bfaccount)
        organization_name = bf.context.name
        organization_id = bf.context.id
        list_users = bf._api._get('/organizations/' + str(organization_id) + '/members')
        list_users_first_last = []
        for i in range(len(list_users)):
                first_last = list_users[i]['firstName'] + ' ' + list_users[i]['lastName']
                list_users_first_last.append(first_last)
        list_users_first_last.sort() # Returning the list of users in alphabetical order
        return list_users_first_last
    except Exception as e:
        raise e


def bf_get_teams(selected_bfaccount):
    """
    Args:
      selected_bfaccount: name of selected Blackfynn acccount (string)
    Return:
        list_teams : list of teams (name) associated with the organization of the
        selected Blackfynn account (list of string)
    Action:
        Provides list of teams belonging to the organization of
        the given Blackfynn account
    """
    try:
        bf = Blackfynn(selected_bfaccount)
        organization_name = bf.context.name
        organization_id = bf.context.id
        list_teams = bf._api._get('/organizations/' + str(organization_id) + '/teams')
        list_teams_name = []
        for i in range(len(list_teams)):
                team_name = list_teams[i]['team']['name']
                list_teams_name.append(team_name)
        list_teams_name.sort() # Returning the list of teams in alphabetical order
        return list_teams_name
    except Exception as e:
        raise e


def bf_get_permission(selected_bfaccount, selected_bfdataset):
    """
    Function to get current permission for a selected Blackfynn dataset

    Args:
        selected_bfaccount: name of selected Blackfynn acccount (string)
        selected_bfdataset: name of selected Blackfynn dataset (string)
    Return:
        list_permission: list of permission (first name -- last name -- role) associated with the
        selected dataset (list of strings)
    """
    error = ''

    try:
        bf = Blackfynn(selected_bfaccount)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn account'
        raise Exception(error)

    c = 0

    try:
        myds = bf.get_dataset(selected_bfdataset)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn dataset' + '<br>'
        c += 1

    try:
        if c > 0:
            raise Exception(error)
        else:
            # user permissions
            selected_dataset_id = myds.id
            list_dataset_permission = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/users')
            list_dataset_permission_first_last_role = []
            for i in range(len(list_dataset_permission)):
                first_name = list_dataset_permission[i]['firstName']
                last_name = list_dataset_permission[i]['lastName']
                role = list_dataset_permission[i]['role']
                list_dataset_permission_first_last_role.append('User ' +  first_name + ' ' + last_name + ' , role: ' + role)

            # team permissions
            list_dataset_permission_teams = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/teams')
            for i in range(len(list_dataset_permission_teams)):
                team_keys = list(list_dataset_permission_teams[i].keys())
                if 'role' in team_keys:
                    team_name = list_dataset_permission_teams[i]['name']
                    team_role = list_dataset_permission_teams[i]['role']
                    list_dataset_permission_first_last_role.append('Team ' + team_name + ' , role: ' + team_role)

            # Organization permissions
            list_dataset_permission_organizations = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/organizations')
            if type(list_dataset_permission_organizations) is dict:
                    organization_keys = list(list_dataset_permission_organizations.keys())
                    if 'role' in organization_keys:
                        organization_name = list_dataset_permission_organizations['name']
                        organization_role = list_dataset_permission_organizations['role']
                        list_dataset_permission_first_last_role.append('Organization ' + organization_name + ' , role: ' + organization_role)
            else:
                for i in range(len(list_dataset_permission_organizations)):
                    organization_keys = list(list_dataset_permission_organizations[i].keys())
                    if 'role' in organization_keys:
                        organization_name = list_dataset_permission_organizations[i]['name']
                        organization_role = list_dataset_permission_organizations[i]['role']
                        list_dataset_permission_first_last_role.append('Organization ' + organization_name + ' , role: ' + organization_role)

            return list_dataset_permission_first_last_role

    except Exception as e:
        raise e

def bf_get_permission(selected_bfaccount, selected_bfdataset):

    """
    Function to get permission for a selected dataset

    Args:
        selected_bfaccount: name of selected Blackfynn acccount (string)
        selected_bfdataset: name of selected Blackfynn dataset (string)
    Output:
        list_permission: list of permission (first name -- last name -- role) associated with the
        selected dataset (list of string)
    """
    error = ''

    try:
        bf = Blackfynn(selected_bfaccount)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn account'
        raise Exception(error)

    c = 0

    try:
        myds = bf.get_dataset(selected_bfdataset)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn dataset' + '<br>'
        c += 1

    try:
        if c > 0:
            raise Exception(error)
        else:
            # user permissions
            selected_dataset_id = myds.id
            list_dataset_permission = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/users')
            list_dataset_permission_first_last_role = []
            for i in range(len(list_dataset_permission)):
                first_name = list_dataset_permission[i]['firstName']
                last_name = list_dataset_permission[i]['lastName']
                role = list_dataset_permission[i]['role']
                list_dataset_permission_first_last_role.append('User ' +  first_name + ' ' + last_name + ' , role: ' + role)

            # team permissions
            list_dataset_permission_teams = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/teams')
            for i in range(len(list_dataset_permission_teams)):
                team_keys = list(list_dataset_permission_teams[i].keys())
                if 'role' in team_keys:
                    team_name = list_dataset_permission_teams[i]['name']
                    team_role = list_dataset_permission_teams[i]['role']
                    list_dataset_permission_first_last_role.append('Team ' + team_name + ' , role: ' + team_role)

            # Organization permissions
            list_dataset_permission_organizations = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/organizations')
            if type(list_dataset_permission_organizations) is dict:
                    organization_keys = list(list_dataset_permission_organizations.keys())
                    if 'role' in organization_keys:
                        organization_name = list_dataset_permission_organizations['name']
                        organization_role = list_dataset_permission_organizations['role']
                        list_dataset_permission_first_last_role.append('Organization ' + organization_name + ' , role: ' + organization_role)
            else:
                for i in range(len(list_dataset_permission_organizations)):
                    organization_keys = list(list_dataset_permission_organizations[i].keys())
                    if 'role' in organization_keys:
                        organization_name = list_dataset_permission_organizations[i]['name']
                        organization_role = list_dataset_permission_organizations[i]['role']
                        list_dataset_permission_first_last_role.append('Organization ' + organization_name + ' , role: ' + organization_role)

            return list_dataset_permission_first_last_role

    except Exception as e:
        raise e

def bf_add_permission(selected_bfaccount, selected_bfdataset, selected_user, selected_role):

    """
    Function to add/remove permission for a suser to a selected dataset

    Args:
        selected_bfaccount: name of selected Blackfynn acccount (string)
        selected_bfdataset: name of selected Blackfynn dataset (string)
        selected_user: name (first name -- last name) of selected Blackfynn user (string)
        selected_role: desired role ('manager', 'viewer', 'editor', 'remove current permission') (string)
    Return:
        success or error message (string)
    """

    error = ''
    try:
        bf = Blackfynn(selected_bfaccount)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn account'
        raise Exception(error)

    c = 0
    try:
        myds = bf.get_dataset(selected_bfdataset)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn dataset' + '<br>'
        c += 1

    try:
        organization_name = bf.context.name
        organization_id = bf.context.id
        list_users = bf._api._get('/organizations/' + str(organization_id) + '/members')
        dict_users = {}
        list_users_firstlast = []
        for i in range(len(list_users)):
            list_users_firstlast.append(list_users[i]['firstName'] + ' ' + list_users[i]['lastName'] )
            dict_users[list_users_firstlast[i]] = list_users[i]['id']
        if selected_user not in list_users_firstlast:
            error = error + 'Error: Please select a valid user' + '<br>'
            c += 1
    except Exception as e:
        raise e

    if selected_role not in ['manager', 'viewer', 'editor', 'owner', 'remove current permission']:
        error = error + 'Error: Please select a valid role' + '<br>'
        c += 1

    if c > 0:
        raise Exception(error)
    else:
        try:
            selected_dataset_id = myds.id
            selected_user_id = dict_users[selected_user]

            # check that currently logged in user is a manager or a owner of the selected dataset (only manager and owner can change dataset permission)
            current_user = bf._api._get('/user')
            first_name_current_user = current_user['firstName']
            last_name_current_user = current_user['lastName']
            list_dataset_permission = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/users')
            c = 0
            for i in range(len(list_dataset_permission)):
                first_name = list_dataset_permission[i]['firstName']
                last_name = list_dataset_permission[i]['lastName']
                role = list_dataset_permission[i]['role']
                user_id = list_dataset_permission[i]['id']
                if (first_name == first_name_current_user and last_name == last_name_current_user):
                    if role not in ['owner', 'manager']:
                        raise Exception('Error: you must be dataset owner or manager to change its permissions')
                    elif selected_role == 'owner' and role != 'owner':
                        raise Exception('Error: you must be dataset owner to change the ownership')
                    else:
                        c += 1
                #check if selected user is owner, dataset permission cannot be changed for owner
                if user_id == selected_user_id and role == 'owner':
                    raise Exception("Error: owner's permission cannot be changed")

            if (c == 0):
                raise Exception('Error: you must be dataset owner or manager to change its permissions')

            if (selected_role == 'remove current permission'):

                bf._api.datasets._del('/' + str(selected_dataset_id) + '/collaborators/users'.format(dataset_id = selected_dataset_id),
                              json={'id': selected_user_id})
                return "Permission removed for " + selected_user
            elif (selected_role == 'owner'):
                #check if currently logged in user is owner of selected dataset (only owner can change owner)

                # change owner
                bf._api.datasets._put('/' + str(selected_dataset_id) + '/collaborators/owner'.format(dataset_id = selected_dataset_id),
                              json={'id': selected_user_id})
                return "Permission " + "'" + selected_role + "' " +  " added for " + selected_user
            else:
                bf._api.datasets._put('/' + str(selected_dataset_id) + '/collaborators/users'.format(dataset_id = selected_dataset_id),
                              json={'id': selected_user_id, 'role': selected_role})
                return "Permission " + "'" + selected_role + "' " +  " added for " + selected_user
        except Exception as e:
                raise e


def bf_add_permission_team(selected_bfaccount, selected_bfdataset, selected_team, selected_role):

    """
    Function to add/remove permission fo a team to a selected dataset

    Args:
        selected_bfaccount: name of selected Blackfynn acccount (string)
        selected_bfdataset: name of selected Blackfynn dataset (string)
        selected_team: name of selected Blackfynn team (string)
        selected_role: desired role ('manager', 'viewer', 'editor', 'remove current permission') (string)
    Return:
        success or error message (string)
    """

    error = ''

    try:
        bf = Blackfynn(selected_bfaccount)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn account'
        raise Exception(error)

    c = 0

    try:
        myds = bf.get_dataset(selected_bfdataset)
    except Exception as e:
        error = error + 'Error: Please select a valid Blackfynn dataset' + '<br>'
        c += 1

    try:
        organization_name = bf.context.name
        organization_id = bf.context.id
        list_teams = bf._api._get('/organizations/' + str(organization_id) + '/teams')
        dict_teams = {}
        list_teams_name = []
        for i in range(len(list_teams)):
                list_teams_name.append(list_teams[i]['team']['name'])
                dict_teams[list_teams_name[i]] = list_teams[i]['team']['id']
        if selected_team not in list_teams_name:
           error = error + 'Error: Please select a valid team' + '<br>'
           c += 1
    except Exception as e:
        raise e

    if selected_role not in ['manager', 'viewer', 'editor', 'remove current permission']:
        error = error + 'Error: Please select a valid role' + '<br>'
        c += 1

    if c > 0:
        raise Exception(error)
    else:
        try:
            selected_dataset_id = myds.id
            selected_team_id = dict_teams[selected_team]

            # check that currently logged in user is a manager or a owner of the selected dataset (only manager and owner can change dataset permission)
            current_user = bf._api._get('/user')
            first_name_current_user = current_user['firstName']
            last_name_current_user = current_user['lastName']
            list_dataset_permission = bf._api._get('/datasets/' + str(selected_dataset_id) + '/collaborators/users')
            c = 0
            for i in range(len(list_dataset_permission)):
                first_name = list_dataset_permission[i]['firstName']
                last_name = list_dataset_permission[i]['lastName']
                role = list_dataset_permission[i]['role']
                user_id = list_dataset_permission[i]['id']
                if (first_name == first_name_current_user and last_name == last_name_current_user):
                    if role not in ['owner', 'manager']:
                        raise Exception('Error: you must be dataset owner or manager to change its permissions')
                    else:
                        c += 1
            if (c == 0):
                raise Exception('Error: you must be dataset owner or manager to change its permissions')

            if (selected_role == 'remove current permission'):

                bf._api.datasets._del('/' + str(selected_dataset_id) + '/collaborators/teams'.format(dataset_id = selected_dataset_id),
                              json={'id': selected_team_id})
                return "Permission removed for " + selected_team
            else:
                bf._api.datasets._put('/' + str(selected_dataset_id) + '/collaborators/teams'.format(dataset_id = selected_dataset_id),
                              json={'id': selected_team_id, 'role': selected_role})
                return "Permission " + "'" + selected_role + "' " +  " added for " + selected_team
        except Exception as e:
                raise e
