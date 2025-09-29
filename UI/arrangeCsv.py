import os
import pandas as pd

def arrange_csv(input_csv_path, output_csv_path):
    """
    Processes the RFID CSV file by skipping the first two rows, 
    using the third row as header, renaming the columns, 
    and saving the result as a new CSV file.
    
    :param input_path: Path to the input CSV file
    :param output_path: Path to save the output CSV file
    """
    # Read the CSV, skipping the first two rows (third row becomes header)
    df = pd.read_csv(input_csv_path, skiprows=2)

    # Rename columns to the specified names
    new_columns = [
        "Timestamp",
        "EPC",
        "TID",
        "Antenna",
        "RSSI",
        "Frequency",
        "Hostname",
        "PhaseAngle",
        "DopplerFrequency",
        "CRHandle"
    ]
    df.columns = new_columns
    
    # Save to new CSV without index
    df.to_csv(output_csv_path, index=False)

    return df

