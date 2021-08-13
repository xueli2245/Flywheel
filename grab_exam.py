import os
import glob
import pydicom
import sys

replaceFolder = lambda x,y : x.replace( os.path.dirname(x), y )

database_folder = '/Users/lixue/temp/sCT_test'

# check arguments
validArgs = True
grabFullExam = False
studyUID = '' # 3137
outputFolder = ''
if len(sys.argv) == 4:
    if sys.argv[1].lower() == 'pet':
        grabFullExam = False
    elif sys.argv[1].lower() == 'full':
        grabFullExam = True
    else:
        print('Output type must be specified. Exiting.')
        validArgs = False

    studyUID = sys.argv[2]
    outputFolder = os.path.abspath( sys.argv[3] )
    if not os.path.isdir( outputFolder ):
        print('Output folder ' + outputFolder + ' does not exist. Exiting.')
        validArgs = False
else:
    print('Invalid inputs. Exiting.')
    validArgs = False

if not validArgs:
    print('* grab_exam will scour the database to find the necessary PET files for offline reconstruction.')
    print('* PET files includes the sinogram, list, and relevant header files, including those needed for AC.')
    print('* grab_exam will take the specified DICOM Study UID and write the structure of the files necessary for')
    print('* offline reconstruction as symbolic links in the specified output folder. Then, from the linked')
    print('* folder structure, files can be transferred to an offline workstation for Duetto reconstruction.')
    print('*')
    print('* To use grab_exam, use the following command line:')
    print('')
    print('      grab_exam <pet|full> STUDY_UID OUTPUT_FOLDER')
    print('')
    print('  * Where the following inputs are required:')
    print('      pet or full -- if specified as pet, only the files necessary for a PET recon will be included')
    print('                  -- if specified as full, all files will be included')
    print('      STUDY_UID -- the study UID you would like to grab. See the tool list_exams')
    print('      OUTPUT_FOLDER -- the output folder where the exam file structure will be placed as symbolic links')
    sys.exit(1)

print('Searching for StudyUID ' + studyUID + '. Symlinked structure will be output to ' + outputFolder + '...')
foundExam = False
foundExamNum = ''
foundExamName = ''
foundExamDesc = ''
exam_other = []
exam_petac = []
exam_petlist = []
exam_petraw = []

# walk through the PATIENT(sCT_0_001)/EXAM(Dicom)/SERIES folder structure (series)
patient_folders = os.listdir(database_folder) # sCT_1_xxx
for curr_patient in patient_folders:          # sCT_1_002
    if 'DS_Store' in curr_patient:
        continue
    exam_folders = os.listdir(os.path.join(database_folder,curr_patient))  # sep
    for curr_exam in exam_folders:                                         # sep
        if 'DS_Store' in curr_exam:
            continue
        series_folders = os.listdir(os.path.join(database_folder,curr_patient,curr_exam)) # series
        for curr_series in series_folders:                                                # series
            if 'DS_Store' in curr_series:
                continue
            print('------------current series is ', curr_series, '------------')
            curr_series_path = os.path.join(database_folder,curr_patient,curr_exam,curr_series)
            # look for the first file that matches the format e.g., *.PTDC.1 or *.MRDC.1
            series_files = glob.glob(os.path.join(curr_series_path,'*.??DC.1.img'))

            # skip empty folders
            if len(series_files) == 0:
                print('-------- empty series files ------------')
                continue

            # choose the first file as the test
            test_file = series_files[0]

            # get the dicom header data using pydicom
            dicomdata = pydicom.read_file(test_file)
            curr_series_uid = dicomdata[0x0020,0x000e].value
            curr_modality = dicomdata[0x0008,0x0060].value

            # check if this is right Study UID
            print('-------current modality is ', curr_modality)
            if studyUID == dicomdata[0x0020,0x000D].value:
                foundExam = True
                foundExamNum = dicomdata[0x0020,0x0010].value
                foundExamName = dicomdata[0x0010,0x0010].value
                foundExamDesc = dicomdata[0x0008,0x1030].value
            else:
                continue

            # check if PET Raw (Sinogram data)
            if curr_modality == 'GEMS PET RAW':
                exam_petraw.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'sino':[],'sino_hdr':[],'geo':'','geo_hdr':'','norm':'','norm_hdr':'','wcc':'','mrac':[]} )

                # raw pet series, we need to look at each file in this folder
                pet_series_files = glob.glob(os.path.join(curr_series_path,'*.RPDC.*'))
                for curr_rawpetfile in pet_series_files:
                    dicomdata = pydicom.read_file(curr_rawpetfile)

                    # add patient sinogram file (if this file type)
                    if [0x0009,0x1062] in dicomdata:
                        exam_petraw[0]['sino'].append( dicomdata[0x0009,0x1062].value )
                        exam_petraw[0]['sino_hdr'].append( curr_rawpetfile )
                        # check for MRAC links
                        if [0x0023,0x1060] in dicomdata:
                            for i in range(0,len(dicomdata[0x0023,0x1060].value)):
                                if not dicomdata[0x0023,0x1060][i][0x0023,0x1062].value in exam_petraw[0]['mrac']: # do not duplicate entries
                                    exam_petraw[0]['mrac'].append(dicomdata[0x0023,0x1060][i][0x0023,0x1062].value)

                    # set the norm or geo (if this file type)
                    if [0x0017,0x1005] in dicomdata:
                        if "PET 3D Norm" in dicomdata[0x0017,0x1005].value:
                            # norm on PETMR is identified this way
                            exam_petraw[0]['norm'] = dicomdata[0x0017,0x1007].value
                            exam_petraw[0]['norm_hdr'] = curr_rawpetfile
                        elif "3D Geometric" in dicomdata[0x0017,0x1005].value:
                            exam_petraw[0]['geo'] = dicomdata[0x0017,0x1007].value
                            exam_petraw[0]['geo_hdr'] = curr_rawpetfile
                        elif [0x0017,0x1006] in dicomdata:
                            if 2 == dicomdata[0x0017,0x1006].value:
                                # norm on DMI is identified this way
                                exam_petraw[0]['norm'] = dicomdata[0x0017,0x1007].value
                                exam_petraw[0]['norm_hdr'] = curr_rawpetfile

                    # set the WCC (if this file type)
                    if [0x0019,0x1001] in dicomdata:
                        exam_petraw[0]['wcc'] = curr_rawpetfile

            # check if PET List
            elif curr_modality == 'GEMS PET LST':
                exam_petlist.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'list':[],'list_hdr':[],'geo':'','geo_hdr':'','norm':'','norm_hdr':'','wcc':'','mrac':[]} )

                # list pet series, we need to look at each file in this folder
                pet_series_files = glob.glob(os.path.join(curr_series_path,'*.RPDC.*'))
                for curr_rawpetfile in pet_series_files:
                    dicomdata = pydicom.read_file(curr_rawpetfile)

                    # add list file (if this file type)
                    if [0x0009,0x10da] in dicomdata:
                        exam_petlist[0]['list'].append( dicomdata[0x0009,0x10da].value )
                        exam_petlist[0]['list_hdr'].append( curr_rawpetfile )
                        # check for    MRAC links
                        if [0x0023,0x1060] in dicomdata:
                            for i in range(0,len(dicomdata[0x0023,0x1060].value)):
                                if not dicomdata[0x0023,0x1060][i][0x0023,0x1062].value in exam_petlist[0]['mrac']: # do not duplicate entries
                                    exam_petlist[0]['mrac'].append(dicomdata[0x0023,0x1060][i][0x0023,0x1062].value)

                    # set the norm or geo (if this file type)
                    if [0x0017,0x1005] in dicomdata:
                        if "PET 3D Norm" in dicomdata[0x0017,0x1005].value:
                            # norm on PETMR is identified this way
                            exam_petlist[0]['norm'] = dicomdata[0x0017,0x1007].value
                            exam_petlist[0]['norm_hdr'] = curr_rawpetfile
                        elif "3D Geometric" in dicomdata[0x0017,0x1005].value:
                            exam_petlist[0]['geo'] = dicomdata[0x0017,0x1007].value
                            exam_petlist[0]['geo_hdr'] = curr_rawpetfile
                        elif [0x0017,0x1006] in dicomdata:
                            if 2 == dicomdata[0x0017,0x1006].value:
                                # norm on DMI/D710 is identified this way
                                exam_petlist[0]['norm'] = dicomdata[0x0017,0x1007].value
                                exam_petlist[0]['norm_hdr'] = curr_rawpetfile

                    # set the WCC (if this file type)
                    if [0x0019,0x1001] in dicomdata:
                        exam_petlist[0]['wcc'] = curr_rawpetfile

            # check if a CT file, needed for CTAC
            elif curr_modality == 'CT':
                 exam_petac.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'folder':curr_series_path,'modality':curr_modality} )

            # check if an MRAC file, needed for MRAC
            elif curr_modality == 'MR':
                 if "MRAC" in dicomdata[0x0008,0x103e].value:
                    print('----------MRAC in ', dicomdata[0x0008,0x103e].value)
                    exam_petac.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'folder':curr_series_path,'modality':curr_modality} )
                 elif "ACMAP" in dicomdata[0x0008,0x0008].value:
                    print('----------ACMAP in ', dicomdata[0x0008,0x103e].value)
                    exam_petac.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'folder':curr_series_path,'modality':curr_modality} )
                 else:
                    print('----------none of MRAC or ACMAP were found in ', dicomdata[0x0008,0x103e].value, ' and ', dicomdata[0x0008,0x0008].value)
                    exam_other.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'folder':curr_series_path,'modality':curr_modality} )

            else:
                exam_other.insert( 0, {'series_uid':curr_series_uid,'series_num':dicomdata[0x0020,0x0011].value,'series_desc':dicomdata[0x0008,0x103e].value,'folder':curr_series_path,'modality':curr_modality} )


if foundExam:
    print('Exam found')
    print('  Exam:' + foundExamNum)
    print('  Name:' + str(foundExamName))
    print('  Desc:' + str(foundExamDesc))
    print('  petraw:' + str(exam_petraw))
    print('  petlist:' + str(exam_petlist))
    print('  petac:' + str(exam_petac))
    print('  petother:' + str(exam_other))

    # change study uid to examNum
    examOutFolder = os.path.join( outputFolder, foundExamNum )
    if not os.path.exists(examOutFolder):
        os.mkdir(examOutFolder)

    info_file = open( os.path.join(examOutFolder,'info.txt'), 'a+' )
    info_file.write( 'StudyUID=' + studyUID + '\n' )
    info_file.write( 'Exam=' + foundExamNum + '\n' )
    info_file.write( 'Name=' + str(foundExamName) + '\n' )
    info_file.write( 'Desc=' + foundExamDesc + '\n' )

    for A in exam_petraw:
        currFolder = os.path.join( examOutFolder, 'PT_SINO')
        if not os.path.isdir(currFolder):
            os.mkdir(currFolder)

        currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']) )
        if not os.path.exists(currFolder):
            os.mkdir( currFolder )
        info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )

        calFolder = os.path.join( currFolder, 'calFiles' )
        if not os.path.exists(calFolder):
            os.mkdir( calFolder )
        os.symlink( A['norm'], os.path.join(calFolder,'norm3d') )

        currFolder = os.path.join( currFolder, 'raw' )
        if not os.path.exists(currFolder):
            os.mkdir( currFolder )
        for a in A['sino']:
            os.symlink( a, replaceFolder(a,currFolder) )
        for a in A['sino_hdr']:
            os.symlink( a, replaceFolder(a,currFolder) )
        os.symlink( A['wcc'], replaceFolder(A['wcc'], currFolder) )
        os.symlink( A['geo_hdr'], replaceFolder(A['geo_hdr'], currFolder) )
        os.symlink( A['norm_hdr'], replaceFolder(A['norm_hdr'], currFolder) )

        if 'mrac' in A:
            if len(A['mrac'])>0:
                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC' )
                os.mkdir( currFolder )
                for curr_mrac_series in A['mrac']:
                    foundMRAC = False
                    for a in exam_petac:
                        if curr_mrac_series == a['series_num']:
                            # this is a matching series for this PET scan
                            mrac_station = [int(s) for s in a['series_desc'].split() if s.isdigit()]
                            if ("FAT: MRAC" in a['series_desc']) or ("FAT: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC', 'FAT-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("InPhase: MRAC" in a['series_desc']) or ("InPhase: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC', 'InPhase-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("OutPhase: MRAC" in a['series_desc']) or ("OutPhase: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC', 'OutPhase-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("WATER: MRAC" in a['series_desc']) or ("WATER: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC', 'WATER-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("ZTE" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'MRAC', 'ZTE-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a

                    if not foundMRAC:
                        print('Unidentified MRAC series ' + str(curr_mrac_series) + ' for PET series ' + str(A['series_num']) + '. Exiting.')
                        sys.exit(1)
                    else:
                        info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
                        if not os.path.isdir(currFolder):
                            os.mkdir( currFolder )
                        series_files = glob.glob(os.path.join(found_mrac_series['folder'],'*.??DC.*'))
                        for curr_file in series_files:
                            os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

    for A in exam_petlist:
        currFolder = os.path.join( examOutFolder, 'PT_LIST')
        if not os.path.isdir(currFolder):
            os.mkdir(currFolder)

        currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']) )
        if not os.path.isdir(currFolder):
            os.mkdir( currFolder )
        info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )

        calFolder = os.path.join( currFolder, 'calFiles' )
        if not os.path.isdir(calFolder):
            os.mkdir( calFolder )
        os.symlink( A['norm'], os.path.join(calFolder,'norm3d') )

        currFolder = os.path.join( currFolder, 'list' )
        if not os.path.isdir(currFolder):
            os.mkdir( currFolder )
        for a in A['list']:
            os.symlink( a, replaceFolder(a,currFolder) )
        for a in A['list_hdr']:
            os.symlink( a, replaceFolder(a,currFolder) )
        os.symlink( A['wcc'], replaceFolder(A['wcc'], currFolder) )
        os.symlink( A['geo_hdr'], replaceFolder(A['geo_hdr'], currFolder) )
        os.symlink( A['norm_hdr'], replaceFolder(A['norm_hdr'], currFolder) )

        if 'mrac' in A:
            if len(A['mrac'])>0:
                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC' )
                if not os.path.isdir(currFolder):
                    os.mkdir( currFolder )
                for curr_mrac_series in A['mrac']:
                    foundMRAC = False
                    for a in exam_petac:
                        if curr_mrac_series == a['series_num']:
                            # this is a matching series for this PET scan
                            mrac_station = [int(s) for s in a['series_desc'].split() if s.isdigit()]
                            if ("FAT: MRAC" in a['series_desc']) or ("FAT: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC', 'FAT-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("InPhase: MRAC" in a['series_desc']) or ("InPhase: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC', 'InPhase-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("OutPhase: MRAC" in a['series_desc']) or ("OutPhase: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC', 'OutPhase-' + str(mrac_station[0]) )
                                foundMRAC = True
                            elif ("WATER: MRAC" in a['series_desc']) or ("WATER: Q.MRAC" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC', 'WATER-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a
                            elif ("ZTE" in a['series_desc']):
                                currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'MRAC', 'ZTE-' + str(mrac_station[0]) )
                                foundMRAC = True
                                found_mrac_series = a

                    if not foundMRAC:
                        print('Unidentified MRAC series ' + str(curr_mrac_series) + ' for PET series ' + str(A['series_num']) + '. Exiting.')
                        sys.exit(1)
                    else:
                        info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
                        if not os.path.isdir(currFolder):
                            os.mkdir( currFolder )
                        series_files = glob.glob(os.path.join(found_mrac_series['folder'],'*.??DC.*'))
                        for curr_file in series_files:
                            os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

    # check if there is just one series with name 'CTAC'
    num_ctac_series = 0
    for A in exam_petac:
        if A['modality'] == 'CT':
            if 'CTAC' in A['series_desc']:
                num_ctac_series = num_ctac_series+1
                a = A
    if num_ctac_series == 1:
        # this must be the one CTAC, otherwise the user will have to figure out the best CTAC, which will be in the 'CT' folder
        for A in exam_petraw:
            currFolder = os.path.join( examOutFolder, 'PT_SINO', str(A['series_num']), 'CTAC' )
            if not os.path.isdir(currFolder):
                os.mkdir( currFolder )
            info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
            series_files = glob.glob(os.path.join(a['folder'],'*.??DC.*'))
            for curr_file in series_files:
                os.symlink( curr_file, replaceFolder(curr_file, currFolder) )
        for A in exam_petlist:
            currFolder = os.path.join( examOutFolder, 'PT_LIST', str(A['series_num']), 'CTAC' )
            if not os.path.isdir(currFolder):
                os.mkdir( currFolder )
            info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
            series_files = glob.glob(os.path.join(a['folder'],'*.??DC.*'))
            for curr_file in series_files:
                os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

    # loop through exam_petac series
    for A in exam_petac:
        if A['modality'] == 'CT':
            curr_modality = 'CT'
            currFolder = os.path.join(examOutFolder,curr_modality)
            if not os.path.isdir(currFolder):
                os.mkdir(currFolder)

            currFolder = os.path.join(examOutFolder,curr_modality,str(A['series_num']))
            # only do this if folder does not already exist
            if not os.path.isdir(currFolder):
                os.mkdir( currFolder )
                info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
                series_files = glob.glob(os.path.join(A['folder'],'*.??DC.*'))
                for curr_file in series_files:
                    os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

        if A['modality'] == 'MR':
            isLinkedToPET = False
            for B in exam_petraw:
                if 'mrac' in B:
                    if A['series_num'] in B['mrac']:
                        isLinkedToPET= True

            # if this file is not linked to a PET study
            #  lets place it in the 'Other' folder
            if not isLinkedToPET:
                if 'modality' in A:
                    curr_modality = A['modality']
                else:
                    curr_modality = 'Other'

                currFolder = os.path.join(examOutFolder,curr_modality)
                if not os.path.isdir(currFolder):
                    os.mkdir(currFolder)

                currFolder = os.path.join(examOutFolder,curr_modality,str(A['series_num']))
                # only do this if folder does not already exist
                if not os.path.isdir(currFolder):
                    os.mkdir( currFolder )
                    info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
                    series_files = glob.glob(os.path.join(A['folder'],'*.??DC.*'))
                    for curr_file in series_files:
                        os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

    if grabFullExam:
        for A in exam_other:
            if 'modality' in A:
                curr_modality = A['modality']
            else:
                curr_modality = 'Other'
            currFolder = os.path.join(examOutFolder,curr_modality)
            if not os.path.isdir(currFolder):
                os.mkdir(currFolder)

            currFolder = os.path.join(examOutFolder,curr_modality,str(A['series_num']))
            # only do this if folder does not already exist
            if not os.path.isdir(currFolder):
                os.mkdir( currFolder )
                info_file.write( str(A['series_num']) + ',\'' + A['series_desc'] + '\'' + ',\'' + currFolder.replace(examOutFolder,'') + '\'\n' )
                series_files = glob.glob(os.path.join(A['folder'],'*.??DC.*'))
                for curr_file in series_files:
                    os.symlink( curr_file, replaceFolder(curr_file, currFolder) )

    info_file.close()


else:
    print('StudyUID ' + studyUID + ' not found.')
    sys.exit(1)
