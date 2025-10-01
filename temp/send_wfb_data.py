import wfdb
import pandas as pd
import requests
import json
from time import sleep
from pydantic import BaseModel
from utils import butter_bandpass_filter, normalize_to_minus1_1

class ArrayData(BaseModel):
    data: dict
    file_name: str

def get_formated(a):
    temp = {}
    for key in a:
        c = [a[key][b] for b in a[key]]
        temp["description" if key == "lsi_description_gt" else key] = c
    return temp

# Load metadata
df = pd.read_csv("fullfeat1_saved_sample.csv", sep="|")
print(df["studyid"].unique())
patient_id = "P2_0039"
patientdf = df[df["studyid"] == patient_id]
selected_cols = list(patientdf.columns[-7:-1]) + ['lsi_description_gt']
patientdf_subset = json.loads(patientdf[selected_cols].to_json())
patientdf = get_formated(patientdf_subset)

# Load ECG record from PhysioNet
record_name = "118e00"
record = wfdb.rdrecord(record_name, pn_dir="nstdb")
sampling_rate = int(record.fs)
signal_names = record.sig_name
signals = record.p_signal.T  # shape: (n_leads, n_samples)

segment_length = sampling_rate
num_segments = signals.shape[1] // segment_length
indexForDescription = 0

# Define how often to increment description index
segments_per_description = num_segments // len(patientdf["description"])

for index in range(num_segments):
    payload = {}

    print(patientdf["description"])

    # Increment description index every N segments
    if index % segments_per_description == 0:
        indexForDescription += 1

    # Use indexForDescription safely
    current_description = patientdf["description"][min(indexForDescription, len(patientdf["description"]) - 1)]
    payload["lsi_description"] = current_description

    for i, lead_name in enumerate(signal_names):
        segment = signals[i][index * segment_length : (index + 1) * segment_length]
        filtered = butter_bandpass_filter(segment, fs=sampling_rate, lowcut=0.5, highcut=40)
        normalized = normalize_to_minus1_1(filtered)
        time_axis = [t / sampling_rate for t in range(len(normalized))]

        payload[lead_name] = normalized
        payload[f"{lead_name}_time"] = time_axis

    payload["lsi_sampling_rate"] = sampling_rate

    # Attach metadata
    for key in patientdf:
        if indexForDescription == 0:
            value = None if key == "description" else False
        else:
            value = patientdf[key][indexForDescription - 1]
        # if key == "description":
        #     value = next((v for v in patientdf[key] if v is not None), value)
        # else:
        #     value = next((v for v in patientdf[key] if v is not False), value)
        payload[f"lsi_{key}"] = value

    payload_data = ArrayData(data=payload, file_name=patient_id)
    response = requests.post("http://127.0.0.1:5001/data/save_array", json=payload_data.model_dump())
    print(response.content)
    # exit()
    sleep(1)
