from time import sleep
import h5py
import os
import requests
import json
from pydantic import BaseModel
import pandas as pd
from utils import butter_bandpass_filter, normalize_to_minus1_1

def is_multidimensional_list(lst):
    if not isinstance(lst, list):
        return False  # Not even a list
    if not lst:
        return False  # An empty list is not considered multi-dimensional
    
    # Check if at least one element in the list is also a list
    for item in lst:
        if isinstance(item, list):
            return True
    return False

class ArrayData(BaseModel):
    data: dict
    file_name: str

def get_formated(a):
    temp = {}

    for key in a:
        c = []
        for b in a[key]:
            c.append(a[key][b])
        
        if (key == "lsi_description_gt"):
            temp["description"] = c
        else:
            temp[key] = c

    return temp

# Directory containing your processed HDF5 files
dir_url = r"D:\Salman\ecg_visualization\processed_files"
df = pd.read_csv("fullfeat1_saved_sample.csv", sep="|")

patient = "P2s_0275_"

print(df["studyid"].unique())

patientdf1 = df[df["studyid"] == "P2_0039"]
patientdf2 = df[df["studyid"] == "P2_0641"]
# patientdf = df[df["studyid"] == patient[0: -1]]

print(patientdf1)

# Select the last 6 columns plus 'lsi_description_gt'
selected_cols = list(patientdf1.columns[-7:-1]) + ['lsi_description_gt']
patientdf_subset = json.loads(patientdf1[selected_cols].to_json())

patientdf1 = get_formated(patientdf_subset)

# Select the last 6 columns plus 'lsi_description_gt'
selected_cols = list(patientdf2.columns[-7:-1]) + ['lsi_description_gt']
patientdf_subset = json.loads(patientdf2[selected_cols].to_json())

patientdf2 = get_formated(patientdf_subset)

# Filter only matching files
files_names = [f for f in os.listdir(dir_url) if patient in f]

file_number = 1
indexForDescription = -1
for i, file_name in enumerate(files_names):
    if i > 3: break
    file_path = os.path.join(dir_url, file_name)

    data = {}

    indexForDescription += 1

    sampling_rate = 260

    # Read HDF5 file
    with h5py.File(file_path, "r") as file:
        sampling_rate = int(file.attrs["sampling_rate"])
        hospital = str(file.attrs["hospital"])
        is_single_dimensional = str(file.attrs["is_single_dimensional"])

        for key in list(file.keys()):
            for sub_key in list(file[key].keys()):
                cols = list(file[key][sub_key].keys())

                # If any column name contains "LEAD", then it's NOT single-dimensional
                is_single_dimensional = any("LEAD" in col.upper() for col in cols)

                # If any column name contains "LEAD", then it's NOT single-dimensional
                is_single_dimensional = any("SPO2" in col.upper() for col in cols)

                for k in cols:
                    if "time" in k.lower():
                        continue
                    
                    temp_arr = file[key][sub_key][k][:]
                    
                    if (not is_single_dimensional):
                        data[k] = [arr.tolist() for arr in temp_arr]
                    else:
                        # 1-D array: need to segment
                        arr_1d = temp_arr
                        segment_length = 480  # match UMB's segment size
                        num_segments = len(arr_1d) // segment_length

                        # Trim to full segments only
                        arr_trimmed = arr_1d[:num_segments * segment_length]

                        # Reshape to (num_segments, segment_length) and convert to list-of-lists
                        arr_2d = arr_trimmed.reshape(num_segments, segment_length)
                        data[k] = [seg.tolist() for seg in arr_2d]

    # Get number of frames (time slices)
    index = 0
    max_index = len(next(iter(data.values())))

    while index < max_index:
        if i == 0:
            if index > 60:
                break
        else:
            if index > 10:
                break

        payload = {}

        for lead_name, values in data.items():
            if len(values) < 1 or len(values) < (index - 1):
                continue
            # Filter & normalize
            filtered = butter_bandpass_filter(
                data=values[index],
                fs=sampling_rate,
                lowcut=0.5,
                highcut=40
            )
            normalized = normalize_to_minus1_1(filtered)

            # Create time axis (assuming fs is samples/sec)
            fs = len(values[index])  # Replace with actual fs if known
            time_axis = [t / fs for t in range(len(normalized))]

            payload[lead_name] = normalized
            payload[f"{lead_name}_time"] = time_axis
        
        payload["lsi_sampling_rate"] = sampling_rate

        # Attach metadata
        for key in patientdf1:
            if indexForDescription == 0:
                value = None if key == "description" else False
            elif indexForDescription == 1:
                value = patientdf1[key][0]
            else:
                value = patientdf2[key][0]
            # if key == "description":
            #     value = next((v for v in patientdf[key] if v is not None), value)
            # else:
            #     value = next((v for v in patientdf[key] if v is not False), value)
            payload[f"lsi_{key}"] = value

        payload_data = ArrayData(data=payload, file_name=patient)
        # Send payload to HTTP server (POST to localhost:8000/save_array)
        response = requests.post("http://127.0.0.1:5001/data/save_array", json=payload_data.model_dump())

        print(response.content)
        print(f"saved {indexForDescription}")

        # sleep(1)  # Pause before next frame
        index += 1


    file_number += 1