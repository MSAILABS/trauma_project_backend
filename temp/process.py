import h5py
import os
from datetime import datetime

def get_sampling_rate_hospital_from_colnames(columns, inhosp=False):
    # Default sampling rate based on context
    default_rate = 250 if not inhosp else 240
    sampling_rate = default_rate
 
    # Named waveform groupings
    arterial = {"AR1", "AR2", "AR3", "AR4"}
    co2 = {f"CO2w_{i}" for i in range(1, 5)}
    ecg = {f"ECG2w_{i}" for i in range(1, 5)}
    icp = {f"ICP{i}w_{j}" for i in range(1, 5) for j in range(1, 5)}
    ppg = {f"PPGw_{i}" for i in range(1, 5)}
    hosp='UMB'
    if any(s.startswith("ETCO2") for s in columns):
        sampling_rate = 125
    elif any(s in {
        "LeadI", "LeadII", "LeadIII", "Pads",
        "LeadaVR", "LeadaVL", "LeadaVF", "ImpPads"
    } for s in columns):
        sampling_rate = 250
        hosp='UPITT' # todo return hosp
    elif any(s in arterial.union(co2).union(ecg).union(icp).union(ppg) for s in columns):
        sampling_rate = default_rate
 
    return sampling_rate, hosp

def get_sample_time_series(vs_filename='P1s_0001_00_vs_st0_dt600_obfca9af.hdf5',
                           segment_id='obfca9af',
                           case_id='hnbp6d6c'):
    """
    Generate a sample prediction message by reading and processing EHR and VS files.
 
    This function reads from a JSON formatted EHR (Electronic Health Records) file and
    an H5 formatted VS (Vital Signs) file. It then combines information from both files
    into a structured prediction message format, including start and stop times for the
    prediction, EHR data, and processed VS data.
 
    Parameters:
    - ehr_filename (str): The file path to the EHR file in JSON format.
    - vs_filename (str): The file path to the VS file in H5 format.
    - segment_id (str): Unique string identifier for segment.
    - case_id (str): Unique string identifier for case.
 
    Returns:
    - dict: A dictionary containing the combined prediction message with keys for segment ID,
      case ID, EHR data, processed VS data, and start/stop times.
    """
 
    with h5py.File(vs_filename, 'r') as f:
        hdf5_content = {}
        start_time = datetime.now()
 
        def traverse(item, path):
            """
            Recursively traverses through groups and datasets in an H5 file
            to construct a nested dictionary representation of its contents.
 
            Parameters:
            - item: The current H5 group or dataset item to process.
            - path (str): The current path (hierarchical structure) being traversed.
            """
            if isinstance(item, h5py.Group):
                for key in item.keys():
                    traverse(item[key], path + '/' + key)
            elif isinstance(item, h5py.Dataset):
                path_components = path.split('/')[1:]
                current_dict = hdf5_content
                for component in path_components[:-1]:
                    current_dict = current_dict.setdefault(component, {})
                current_dict[path_components[-1]] = item[()]
 
        traverse(f, '/')
 
    stop_time = datetime.now()
 
    return {
 
        "start_time": start_time.isoformat(),
        "stop_time": stop_time.isoformat(),
        "vs": hdf5_content['']
    }

def read_files():
    dir_url = "D:\Salman\ecg_visualization\sample"
    urls = os.listdir(dir_url)

    for url in urls:
        dir_path = os.path.join(dir_url, url)

        if os.path.isfile(dir_path):
            continue

        file_urls = os.listdir(dir_path)

        for file_url in file_urls:
            if not file_url.endswith(".hdf5"):
                continue

            file_path = os.path.join(dir_path, file_url)

            with h5py.File(file_path, "r") as file:
                # data = get_sample_time_series(file_path)
                data = {}
                sampling_rate = 0
                is_single_dimensional = False
                ecgCol = False
                for key in list(file.keys()):
                    if (key == "pre_hospital"):
                        pass

                    data[key] = {}
                    for sub_key in ["signal", "trends"]:
                        data[key][sub_key] = {}

                        try:
                            cols = [c for c in file[key][sub_key].keys()]
                        except Exception:
                            continue

                        s_r, hosp = get_sampling_rate_hospital_from_colnames(columns=cols, inhosp=(True if key == "in_hospital" else False))
                        sampling_rate = s_r
                        hospital = hosp

                        is_lead = False

                        for col in cols:
                            if col.startswith("Lead"):
                                is_lead = True

                        for col in cols:
                            col: str = col

                            if is_lead:
                                if col.startswith("ECG") or col.startswith("PPG"):
                                    continue
                            else:
                                if col.startswith("Lead") or col.startswith("SPO2"):
                                    continue

                            isEcgData = col.startswith("ECG") or col.startswith("Lead") or col.startswith("PPG") or col.startswith("SPO2")
                            
                            if col.startswith("Lead") or col.startswith("SPO2"):
                                is_single_dimensional = True

                            if isEcgData == False:
                                continue
                            elif col.startswith("ECG") and ecgCol:
                                continue
                            else:
                                print("ecg data")

                                arr = file[key][sub_key][col][:]

                                data[key][sub_key][col] = arr


                                print(arr.shape)
                            
                            if col.startswith("ECG"):
                                ecgCol = True
                
                head, tail = os.path.split(file_path)
                new_file = os.path.join("processed_files", tail)

                with h5py.File(new_file, "w") as f:
                    f.attrs["sampling_rate"] = sampling_rate
                    f.attrs["hospital"] = hospital
                    f.attrs["is_single_dimensional"] = is_single_dimensional
                    for key in data:
                        grp = f.create_group(key)  # Create top-level group

                        for sub_key in data[key]:
                            sub_grp = grp.create_group(sub_key)  # Create subgroup like 'signal' or 'trends'

                            for col in data[key][sub_key]:
                                arr = data[key][sub_key][col]

                                # Save dataset
                                sub_grp.create_dataset(col, data=arr)




read_files()
