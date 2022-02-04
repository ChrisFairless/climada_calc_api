import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

from climada.entity import ImpactFunc, ImpactFuncSet, ImpfTropCyclone
from climada.util.api_client import Client
from climada.engine.impact import Impact

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# --------------------------------------------------------

# SETTINGS

sample_settings = {
    'country': 'HTI',  # Haiti
    'hazard_type': 'tropical_cyclone',
    'exposure_type': 'people',
    'scenario_name': 'rcp45',
    'scenario_year': 2060,
    'n_tracks': 10,
    'return_period': 100
}

output_directory = sys.argv[1]

# --------------------------------------------------------

map_haz_out_path = Path(output_directory, 'map_haz_rp.csv')
exceedance_haz_out_path = Path(output_directory, 'exceedance_haz.csv')
map_exp_out_path = Path(output_directory, 'map_exp.csv')
map_imp_out_path = Path(output_directory, 'map_imp_rp.csv')
exceedance_imp_out_path = Path(output_directory, 'exceedance_imp.csv')
all_paths = [map_haz_out_path, exceedance_haz_out_path, map_exp_out_path, map_imp_out_path, exceedance_imp_out_path]

if all(os.path.exists(p) for p in all_paths):
    LOGGER.info('Sample files already exist. Exiting')
    exit()

if not os.path.exists(output_directory):
    LOGGER.info("Creating output directory: " + output_directory)
    os.mkdir(output_directory)

return_periods = [10, 50, 100, 150, 200, 250]
i_rp = [i for i, rp in enumerate(return_periods) if rp == sample_settings['return_period']][0]

client = Client()
LOGGER.info('Creating API sample data')
LOGGER.info('Getting hazard data')
haz = client.get_hazard(sample_settings['hazard_type'],
                        properties={'spatial_coverage': 'country',
                                    'country_iso3alpha': sample_settings['country'],
                                    'nb_synth_tracks': str(sample_settings['n_tracks']),
                                    'climate_scenario': sample_settings['scenario_name'],
                                    'ref_year': str(sample_settings['scenario_year'])})

LOGGER.info('Calculating climatologies')

haz_rp = haz.local_exceedance_inten([sample_settings['return_period']])[0]

haz_df = pd.DataFrame({'lat': haz.centroids.lat,
                       'lon': haz.centroids.lon,
                       'intensity': haz_rp})
haz_df.to_csv(map_haz_out_path)


haz_ex_df = pd.DataFrame({'intensity': np.max(haz.intensity, axis=1).todense().A1,
                          'frequency': haz.frequency})
haz_ex_df = haz_ex_df[haz_ex_df['intensity'] > 0]
haz_ex_df = haz_ex_df.sort_values(by='intensity', ascending=False)
haz_ex_df['return_period'] = 1/np.cumsum(haz_ex_df['frequency'])
haz_ex_df = haz_ex_df.drop(columns='frequency')
haz_ex_df.to_csv(exceedance_haz_out_path)




# Set up exposures
LOGGER.info('Getting exposure data')
if sample_settings['exposure_type'] == 'assets':
    exponents = '(1,1)'
    fin_mode = 'pc'
    impf = ImpfTropCyclone.from_emanuel_usa()
elif sample_settings['exposure_type'] == 'people':
    exponents = '(0,1)'
    fin_mode = 'pop'
    step_threshold = 50
    impf = ImpactFunc.from_step_impf(intensity=(0, step_threshold, 200))  # TODO make this better
    impf.name = 'Step function ' + str(step_threshold) + ' m/s'
else:
    raise ValueError("exposure_type must be either 'assets' or 'people'")

# Query exposure data
exp = client.get_exposures(exposures_type='litpop', properties={'spatial_coverage': 'country',
                                                                'country_iso3alpha': sample_settings['country'],
                                                                'exponents': exponents,
                                                                'fin_mode': fin_mode})

exp_df = pd.DataFrame({'lat': exp.gdf.latitude,
                       'lon': exp.gdf.longitude,
                       'value': exp.gdf.value})
exp_df.to_csv(map_exp_out_path)

# map exposures to hazard centroids
LOGGER.info('Mapping to centroids')
centroid_mapping_colname = 'centr_' + haz.tag.haz_type
if centroid_mapping_colname not in exp.gdf.columns:
    exp.assign_centroids(haz, distance='euclidean', threshold=20)

LOGGER.info('Calculating impact')
impf.haz_type = haz.tag.haz_type
impf.unit = haz.units

impf_set = ImpactFuncSet()
impf_set.append(impf)

# Calculate impacts
imp = Impact()
imp.calc(exp, impf_set, haz, save_mat=True)

imp_rp = imp.local_exceedance_imp(return_periods=[sample_settings['return_period']])[0]

ix = imp_rp != 0

imp_df = pd.DataFrame({'lat': exp.gdf['latitude'][ix],
                       'lon': exp.gdf['longitude'][ix],
                       'value': imp_rp[ix]})

imp_df.to_csv(map_imp_out_path)


imp_ex_df = pd.DataFrame({'intensity': np.max(imp.imp_mat, axis=1).todense().A1,
                          'frequency': haz.frequency})
imp_ex_df = imp_ex_df[imp_ex_df['intensity'] > 0]
imp_ex_df = imp_ex_df.sort_values(by='intensity', ascending=False)
imp_ex_df['return_period'] = 1/np.cumsum(imp_ex_df['frequency'])
imp_ex_df = imp_ex_df.drop(columns='frequency')
imp_ex_df.to_csv(exceedance_imp_out_path)
