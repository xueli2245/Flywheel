import pydicom
import os


def sepModality(subj_path, out_folder, sep_folder):
	ori_folder = os.path.join(subj_path, sep_folder)
	files = os.listdir(ori_folder)
	for file in files:
		file_path = os.path.join(ori_folder, file)
		ds = pydicom.dcmread(file_path)

		# for dicom images
		series_folder = os.path.join(out_folder, ds[0x0008,0x0060].value.split(' ')[-1])
		if not os.path.exists(series_folder):
			os.makedirs(series_folder)
		cmd = 'cp ' + file_path + ' ' + series_folder + '/'
		os.system(cmd)


def sepDetailedModality(subj_path, out_folder, sep_folder):
	ori_folder = os.path.join(subj_path, sep_folder)
	files = os.listdir(ori_folder)
	for file in files:
		file_path = os.path.join(ori_folder, file)
		ds = pydicom.dcmread(file_path)

		# modality
		cur_modality = ds[0x0008,0x103e].value

		# for dicom images
		modality_folder = out_folder + '/"' + ds[0x0008,0x103e].value + '"'
		print(modality_folder)
		if not os.path.exists(modality_folder):
			os.makedirs(modality_folder)
		cmd = 'cp ' + file_path + ' ' + '\'' + modality_folder + '\''
		os.system(cmd)


def separateSino(subj_path):
	ori_folder = os.path.join(subj_path, 'sino')
	files = os.listdir(ori_folder)
	for file in files:
		file_path = os.path.join(ori_folder, file)
		ds = pydicom.dcmread(file_path)
		if ds[0x0008,0x0060].value == 'GEMS PET RAW':
			series_folder = sep_folder + 'raw'
			if not os.path.exists(series_folder):
				os.makedirs(series_folder)
			cmd = 'cp ' + file_path + ' ' + series_folder + '/'
			os.system(cmd)
		elif ds[0x0008,0x0060].value == 'GEMS PET LST':
			series_folder = sep_folder + 'list'
			if not os.path.exists(series_folder):
				os.makedirs(series_folder)
			cmd = 'cp ' + file_path + ' ' + series_folder + '/'
			os.system(cmd)
		else:
			print('There is an irrelevant image!')


if __name__ == '__main__':
	subj_path = '/Users/lixue/temp/sCT/sCT_1_002'
	out_folder = subj_path + '/sep'
	sep_folder = 'dicom'
	if not os.path.exists(out_folder):
		os.makedirs(out_folder)
	sepDetailedModality(subj_path, out_folder, sep_folder)

