import pandas as pd
import os


SLIDER_SPEED = 0.069
antenna_z = [0, 0.5]
antenna_y = 0
c = 3e8

def generate_number_letter_report(input_file: str, output_suffix: str = "_report"):
    # EPC mapping
    epc_map = {
        "E2806995000040058378221E": "A",
        "E2806995000040058378661E": "B",
        "E28069950000400583786A1E": "C",
        "E28069950000400583787E1E": "D",
        "E2806995000040058378821E": "E",
        "E2806995000040058378961E": "F",
    }

    # Read CSV
    df = pd.read_csv(input_file)

    # Replace EPC with mapped label
    df["EPC"] = df["EPC"].map(epc_map)

    # Sort by Z (descending for top)
    df_sorted = df.sort_values(by="Z", ascending=False)

    # Split into top 3 (highest Z) and bottom 3 (lowest Z)
    top_list = df_sorted.head(3).sort_values(by="X", ascending=True)
    bottom_list = df_sorted.tail(3).sort_values(by="X", ascending=True)

    # Assign numbers
    bottom_list = bottom_list.reset_index(drop=True)
    bottom_list["Number"] = bottom_list.index + 1  # 1–3

    top_list = top_list.reset_index(drop=True)
    top_list["Number"] = top_list.index + 4  # 4–6

    # Combine results
    final_report = pd.concat([bottom_list, top_list], ignore_index=True)

    # Keep only Number and Letter
    final_report = final_report[["Number", "EPC"]]
    final_report.columns = ["Number", "Letter"]

    # Build output path in same folder as input file
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}{output_suffix}{ext}"

    # Save to CSV
    final_report.to_csv(output_file, index=False)

    # Convert to dictionary: {number: letter}
    location_dict = dict(zip(final_report["Number"], final_report["Letter"]))
    return location_dict




