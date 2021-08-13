import pydicom
import os

folder = './dicom'
files = os.listdir(folder)
MR_md = []
MR_sn = []
PT_md = []
PT_sn = []
for file in files:
    path = os.path.join(folder, file)
    ds = pydicom.dcmread(path)
    if ds[0x0008,0x0060].value == 'MR':
        MR_md.append(ds[0x0008,0x103e].value)
        MR_sn.append(ds[0x0020,0x0011].value)
    elif ds[0x0008,0x0060].value == 'PT':
        PT_md.append(ds[0x0008,0x103e].value)
        PT_sn.append(ds[0x0020,0x0011].value)
    else:
        print('error')
MR_final = set(MR_md)
PT_final = set(PT_md)
print('---------MR_final-----------')
for i in MR_final:
    print(i)
print(set(MR_sn))
print('---------PT_final-----------')
for i in PT_final:
    print(i)
print(set(PT_sn))
