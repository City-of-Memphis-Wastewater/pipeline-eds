# src/pipeline_eds/api/eds/conversion_csv.py
import csv
import io
from ...helpers import iso_time

def export_csv_for_results(results: list, idcs: list[str]) -> str:
    """
    Transforms raw EDS historic results into a CSV string.
    """
    if not results or not idcs:
        return ""

    # 1. Collect and sort all unique timestamps
    all_timestamps = set()
    for rows in results:
        for row in rows:
            if row.get("ts") is not None:
                all_timestamps.add(row.get("ts"))
    
    sorted_timestamps = sorted(all_timestamps)

    # 2. Build matrix mapping: timestamp -> { sensor_id: value }
    data_matrix = {ts: {} for ts in sorted_timestamps}
    for idx, rows in enumerate(results):
        sensor_id = idcs[idx]
        for row in rows:
            ts = row.get("ts")
            if ts is not None:
                data_matrix[ts][sensor_id] = row.get("value")

    # 3. Write CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow(["Timestamp"] + idcs)

    # Data rows
    for ts in sorted_timestamps:
        row = [iso_time(ts)] + [data_matrix[ts].get(sensor_id, "") for sensor_id in idcs]
        writer.writerow(row)

    return output.getvalue()
