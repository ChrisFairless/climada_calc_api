
# Generate the sample data files needed for the test api endpoints
# Run before collecting static

import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

from climada.entity import ImpactFunc, ImpactFuncSet, ImpfTropCyclone
from climada.util.api_client import Client
from climada.engine.impact import Impact
import climada.util.coordinates as u_coord

from django.core.management import BaseCommand

from climada_calc.settings import BASE_DIR

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# SETTINGS
sample_settings = {
    'country': 'HTI',  # Haiti
    'hazard_type': 'tropical_cyclone',
    'exposure_type': 'economic_assets',
    'scenario_name': 'rcp45',
    'scenario_year': 2060,
    'n_tracks': 10,
    'return_period': 100
}


def get_round_resolution_1d(x):
    res = u_coord.get_resolution_1d(x)
    recip = 1/res
    if abs(recip - np.round(recip)) < 0.001:
        res = 1/np.round(recip)
    return res


def get_round_resolution(lon, lat):
    return get_round_resolution_1d(lon), get_round_resolution_1d(lat)


class Command(BaseCommand):
    # Show this when the user types help
    help = "Generates sample data needed for the vtest endpoints"

    def handle(self, *args, **options):
        LOGGER.info("Generating sample data needed for the vtest endpoints")

        output_directory = Path(BASE_DIR, 'staticfiles', 'sample_data')

        LOGGER.info("Creating sample datasets")

        map_haz_out_path = Path(output_directory, 'map_haz_rp.csv')
        map_haz_out_path_raster = Path(output_directory, 'map_haz_rp.tif')
        exceedance_haz_out_path = Path(output_directory, 'exceedance_haz.csv')
        map_exp_out_path = Path(output_directory, 'map_exp.csv')
        map_exp_out_path_raster = Path(output_directory, 'map_exp.tif')
        map_imp_out_path = Path(output_directory, 'map_imp_rp.csv')
        map_imp_out_path_raster = Path(output_directory, 'map_imp_rp.tif')
        exceedance_imp_out_path = Path(output_directory, 'exceedance_imp.csv')
        all_paths = [map_haz_out_path, map_haz_out_path_raster, exceedance_haz_out_path, map_exp_out_path,
                     map_exp_out_path_raster, map_imp_out_path, map_imp_out_path_raster, exceedance_imp_out_path]

        def df_to_raster(df, crs):
            """
            This is a shonky replacement for to horror show that is u_coords.points_to_raster. Don't use elsewhere!
            """
            lat = df['lat'].unique()
            lon = df['lon'].unique()
            if len(lat) * len(lon) == df.shape[0]:     # data frame already complete
                return df

            bounds = u_coord.latlon_bounds(df['lat'], df['lon'])
            res = get_round_resolution(df['lon'], df['lat'])
            nrow, ncol, trans = u_coord.pts_to_raster_meta(bounds, res)
            meta = {"width": ncol, "height": nrow, "transform": trans, "crs": crs}

            lon_full, lat_full = u_coord.raster_to_meshgrid(meta['transform'], meta['width'], meta['height'])
            out = pd.DataFrame({'lat': lat_full.flatten(), 'lon': lon_full.flatten()})

            precision = 5   # This is the dangerous bit
            if 10**-precision > 0.1 * min(abs(np.array(res))):
                raise ValueError("Precision too low. Precision: " + str(precision) + "  Resolution: " + str(min(abs(np.array(res)))))

            out['lat_trunc'] = np.round(out['lat'], precision)
            out['lon_trunc'] = np.round(out['lon'], precision)
            df['lat_trunc'] = np.round(df['lat'], precision)
            df['lon_trunc'] = np.round(df['lon'], precision)

            out = out.merge(df.drop(['lat', 'lon'], axis=1, inplace=False), how='left', on=['lat_trunc', 'lon_trunc'])
            out.drop(['lat_trunc', 'lon_trunc'], axis=1)
            return out, meta


        def write_sample_to_raster(df, path, value_column, crs):
            out, meta = df_to_raster(df, crs)
            values = np.array(out[value_column]).reshape(meta['height'], meta['width'])
            u_coord.write_raster(path, values, meta, dtype=np.float32)


        # -----------------------------------------------------

        if all(os.path.exists(p) for p in all_paths):
            LOGGER.info('Sample files already exist. Exiting')
            exit()

        if not os.path.exists(output_directory):
            LOGGER.info("Creating output directory: " + str(output_directory))
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
        write_sample_to_raster(haz_df, map_haz_out_path_raster, 'intensity', haz.centroids.crs)


        haz_ex_df = pd.DataFrame({'intensity': np.max(haz.intensity, axis=1).todense().A1,
                                  'frequency': haz.frequency})
        haz_ex_df = haz_ex_df[haz_ex_df['intensity'] > 0]
        haz_ex_df = haz_ex_df.sort_values(by='intensity', ascending=False)
        haz_ex_df['return_period'] = 1/np.cumsum(haz_ex_df['frequency'])
        haz_ex_df = haz_ex_df.drop(columns='frequency')
        haz_ex_df.to_csv(exceedance_haz_out_path)



        # Set up exposures
        LOGGER.info('Getting exposure data')
        if sample_settings['exposure_type'] == 'economic_assets':
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
            raise ValueError("exposure_type must be either 'economic_assets' or 'people'")

        # Query exposure data
        exp = client.get_exposures(
            exposures_type='litpop_tccentroids',
            properties={'spatial_coverage': 'country',
                        'country_iso3alpha': sample_settings['country'],
                        'exponents': exponents,
                        'fin_mode': fin_mode},
            version='newest',
            status='preliminary'
        )

        exp_df = pd.DataFrame({'lat': exp.gdf.latitude,
                               'lon': exp.gdf.longitude,
                               'value': exp.gdf.value})
        exp_df.to_csv(map_exp_out_path)
        write_sample_to_raster(exp_df, map_exp_out_path_raster, 'value', exp.crs)

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

        exp.gdf['impf_TC'] = 1

        # Calculate impacts
        imp = Impact()
        imp.calc(exp, impf_set, haz, save_mat=True)

        imp_rp = imp.local_exceedance_imp(return_periods=[sample_settings['return_period']])[0]

        ix = imp_rp != 0

        imp_df = pd.DataFrame({'lat': exp.gdf['latitude'][ix],
                               'lon': exp.gdf['longitude'][ix],
                               'value': imp_rp[ix]})

        imp_df.to_csv(map_imp_out_path)
        write_sample_to_raster(imp_df, map_imp_out_path_raster, 'value', haz.centroids.crs)

        imp_ex_df = pd.DataFrame({'intensity': np.max(imp.imp_mat, axis=1).todense().A1,
                                  'frequency': haz.frequency})
        imp_ex_df = imp_ex_df[imp_ex_df['intensity'] > 0]
        imp_ex_df = imp_ex_df.sort_values(by='intensity', ascending=False)
        imp_ex_df['return_period'] = 1/np.cumsum(imp_ex_df['frequency'])
        imp_ex_df = imp_ex_df.drop(columns='frequency')
        imp_ex_df.to_csv(exceedance_imp_out_path)
