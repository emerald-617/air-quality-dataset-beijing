# Analisis Air Quality Dataset - Proyek Latihan Fundamental Analisis Data Dicoding 2026

## Setup Environment - Miniconda
```
conda create --name main-ds python=3.9
conda activate main-ds
pip install -r requirements.txt
```

## Run Streamlit app
```
conda activate main-ds
streamlit run dashboard.py
```

## Deskripsi Data
Dataset `Air-Quality` merupakan kumpulan data menggambarkan pemantauan kualitas udara di lokasi terkontrol di Tiongkok. Dataset ini mencakup data polutan udara per jam dari 12 lokasi pemantauan kualitas udara yang dikendalikan secara nasional. Data kualitas udara berasal dari Beijing Municipal Environmental Monitoring Center. Data meteorologi di setiap lokasi pemantauan kualitas udara dicocokkan dengan stasiun cuaca terdekat dari China Meteorological Administration. Periode waktunya dari 1 Maret 2013 hingga 28 Februari 2017.

#### Keterangan Kolom
* No: row number
* year: year of data in this row 
* month: month of data in this row 
* day: day of data in this row 
* hour: hour of data in this row 
* PM2.5: PM2.5 concentration (ug/m^3)
* PM10: PM10 concentration (ug/m^3)
* SO2: SO2 concentration (ug/m^3)
* NO2: NO2 concentration (ug/m^3)
* CO: CO concentration (ug/m^3)
* O3: O3 concentration (ug/m^3)
* TEMP: temperature (degree Celsius) 
* PRES: pressure (hPa)
* DEWP: dew point temperature (degree Celsius)
* RAIN: precipitation (mm)
* wd: wind direction
* WSPM: wind speed (m/s)
* station: name of the air-quality monitoring site

#### Sumber
- https://www.kaggle.com/datasets/sid321axn/beijing-multisite-airquality-data-set
- https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data
- https://github.com/marceloreis/HTI

## Struktur Repository
```
submission
├───dashboard.py
├───notebook.ipynb
├───README.md
└───requirements.txt
├───url.txt
├───data
| ├───df_daily_station.csv
| ├───df_map.csv
| └───Air-quality-dataset
|   └───PRSA_Data_20130301-20170228
|     ├───PRSA_Data_Aotizhongxin_20130301-20170228
|     ├───PRSA_Data_Changping_20130301-20170228
|     ├───PRSA_Data_Dingling_20130301-20170228
|     ├───PRSA_Data_Dongsi_20130301-20170228
|     ├───PRSA_Data_Guanyuan_20130301-20170228
|     ├───PRSA_Data_Gucheng_20130301-20170228
|     ├───PRSA_Data_Hauairou_20130301-20170228
|     ├───PRSA_Data_Nongzhanguan_20130301-20170228
|     ├───PRSA_Data_Shunyi_20130301-20170228
|     ├───PRSA_Data_Tiantan_20130301-20170228
|     ├───PRSA_Data_Wanliu_20130301-20170228
|     └───PRSA_Data_Wanshouxigong_20130301-20170228
```
