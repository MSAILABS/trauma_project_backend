python rf_predict.py \
    --model_dir ./2026-01-29_10-06-37/models/fold_2 \
    --data_path /home/sagemaker-user/poting/tree_model/ehr_ecg/ehr_ecg_phase1_train_v1_umb.par \
    --output_path predictions.csv \
    --eval


python rf_predict.py \
    --model_dir ./checkpoints_rf_all_features/<timestamp>/models/fold_2 \
    --data_path /path/to/labeled_data.par \
    --eval