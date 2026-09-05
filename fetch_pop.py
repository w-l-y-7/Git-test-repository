import requests, gzip, io, pandas as pd

url = ("https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/"
       "WPP2024_PopulationByAge5GroupSex_Medium.csv.gz")
r = requests.get(url, timeout=180)
print("status", r.status_code, "gz_mb", round(len(r.content)/1e6, 1))
raw = gzip.decompress(r.content)
print("uncompressed_mb", round(len(raw)/1e6, 1))
df = pd.read_csv(io.BytesIO(raw))
print("columns:", list(df.columns))
print("n_rows:", len(df))

c = df[(df["Location"] == "China") & (df["Time"].isin([2016, 2026, 2036]))].copy()
print("china 3-yr rows:", len(c))
print("AgeGrp values:", sorted(c["AgeGrp"].dropna().unique()))
print(c[["Time", "AgeGrp", "PopMale", "PopFemale", "PopTotal"]].head(8).to_string())

out = r"d:\git仓库\Git test repository\china_pop_2016_2026_2036.csv"
c.to_csv(out, index=False)
print("saved:", out)
