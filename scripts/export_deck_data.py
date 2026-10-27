"""Exports the extra numbers the PowerPoint builder needs -> reports/deck_data.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src import config as C

df = pd.read_csv(C.PROCESSED_CSV)
ppsf = "Price_per_SqFt_INR"
mean_all = df[ppsf].mean()


def gap(col):
    """Max-min of group-average price/sqft as % of the overall mean."""
    g = df.groupby(col)[ppsf].mean()
    return round((g.max() - g.min()) / mean_all * 100, 1)


size_band = pd.cut(df["Size_in_SqFt"], list(range(0, 5001, 500)), labels=[f"{a + 1}-{a + 500}" for a in range(0, 5000, 500)])
sb = df.groupby(size_band, observed=True)[ppsf].mean()
df["Size_Band"] = size_band
gaps = {"Owner type": gap("Owner_Type"), "Furnishing": gap("Furnished_Status"), "Facing": gap("Facing"),
        "Property type": gap("Property_Type"), "Transit access": gap("Public_Transport_Accessibility"),
        "State": gap("State"), "City": gap("City"), "Size band": gap("Size_Band")}
out = {"gaps": gaps, "size_band": {"labels": [str(i) for i in sb.index], "values": [round(v) for v in sb.values]},
       "price_size_corr": round(df["Size_in_SqFt"].corr(df["Price_in_Lakhs"]), 3)}
(C.REPORT_DIR / "deck_data.json").write_text(json.dumps(out, indent=2))
print(out["gaps"])
