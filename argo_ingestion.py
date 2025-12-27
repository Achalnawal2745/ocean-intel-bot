"""
ARGO Float Ingestion Module

Provides functions for downloading and ingesting ARGO float data.
Used by both CLI scripts and API endpoints.
"""

import os
import asyncio
import asyncpg
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime
from ftplib import FTP
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# FTP Configuration
FTP_SERVER = 'ftp.ifremer.fr'
FTP_PATH = '/ifremer/argo/dac/incois'
DATA_DIR = 'netcdf_data'

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== HELPER FUNCTIONS ====================

def safe_str(val):
    """Convert to string safely"""
    if isinstance(val, bytes):
        return val.decode('utf-8').strip()
    if isinstance(val, np.ndarray) and val.size == 1:
        return safe_str(val.item())
    return str(val).strip() if val is not None else None

def safe_float(val):
    """Convert to float safely"""
    try:
        return None if pd.isna(val) else float(val)
    except:
        return None

def safe_int(val):
    """Convert to int safely"""
    try:
        if val is None or pd.isna(val):
            return None
        return int(float(str(val)))
    except:
        return None

def safe_date(val):
    """Convert to datetime safely - handles ARGO date format"""
    try:
        if val is None or pd.isna(val):
            return None
        
        # Handle ARGO date format: YYYYMMDDHHMMSS
        if isinstance(val, (bytes, str)):
            date_str = val.decode('utf-8') if isinstance(val, bytes) else str(val)
            date_str = date_str.strip()
            
            if not date_str or date_str == '':
                return None
            
            # Try ARGO format first
            if len(date_str) == 14 and date_str.isdigit():
                result = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                return None if pd.isna(result) else result
            
            # Try ISO format
            result = pd.to_datetime(date_str).to_pydatetime()
            return None if pd.isna(result) else result
        
        # Try pandas conversion
        result = pd.to_datetime(val).to_pydatetime()
        return None if pd.isna(result) else result
    except:
        return None

# ==================== DOWNLOAD FUNCTION ====================

def download_float(float_id: str, data_dir: str = DATA_DIR) -> Dict[str, Any]:
    """
    Download metadata and profile files for a float
    
    Returns:
        {
            "success": bool,
            "float_id": str,
            "files_downloaded": list,
            "message": str,
            "error": str (if failed)
        }
    """
    try:
        logger.info(f"Downloading float {float_id}")
        
        ftp = FTP(FTP_SERVER, timeout=30)
        ftp.login()
        ftp.cwd(f"{FTP_PATH}/{float_id}")
        
        files_to_download = [f'{float_id}_meta.nc', f'{float_id}_prof.nc']
        downloaded = []
        
        for filename in files_to_download:
            local_path = os.path.join(data_dir, filename)
            
            if os.path.exists(local_path):
                logger.info(f"File already exists: {filename}")
                downloaded.append(filename)
                continue
            
            logger.info(f"Downloading {filename}...")
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            
            size = os.path.getsize(local_path)
            logger.info(f"Downloaded {filename} ({size:,} bytes)")
            downloaded.append(filename)
        
        ftp.quit()
        
        return {
            "success": True,
            "float_id": float_id,
            "files_downloaded": downloaded,
            "message": f"Downloaded {len(downloaded)}/2 files for float {float_id}"
        }
        
    except Exception as e:
        logger.error(f"Download failed for float {float_id}: {e}")
        return {
            "success": False,
            "float_id": float_id,
            "error": str(e),
            "message": f"Download failed: {str(e)}"
        }

# ==================== INGESTION FUNCTIONS ====================

async def ingest_metadata(meta_file: str, conn) -> int:
    """Ingest metadata from *_meta.nc file"""
    ds = xr.open_dataset(meta_file)
    
    # Handle both scalar and array platform numbers
    pn_val = ds.PLATFORM_NUMBER.values
    if pn_val.ndim == 0:
        platform_number = int(safe_str(pn_val.item()))
    else:
        platform_number = int(safe_str(pn_val[0]))
    
    # Helper to extract metadata field safely
    def get_field(field_name):
        if field_name not in ds:
            return None
        val = ds[field_name].values
        if val.ndim == 0:
            return val.item()
        return val[0] if len(val) > 0 else None
    
    # Extract all metadata
    metadata = {
        'platform_number': platform_number,
        'float_serial_number': safe_int(get_field('FLOAT_SERIAL_NO')),
        'pi_name': safe_str(get_field('PI_NAME')),
        'project_name': safe_str(get_field('PROJECT_NAME')),
        'deployment_platform': safe_str(get_field('DEPLOYMENT_PLATFORM')),
        'firmware_version': safe_str(get_field('FIRMWARE_VERSION')),
        'float_owner': safe_str(get_field('FLOAT_OWNER')),
        'operating_institute': safe_str(get_field('OPERATING_INSTITUTION')),
        'launch_date': safe_date(get_field('LAUNCH_DATE')),
        'start_date': safe_date(get_field('START_DATE')),
        'end_of_life': safe_date(get_field('END_MISSION_DATE')),
        'launch_latitude': safe_float(get_field('LAUNCH_LATITUDE')),
        'launch_longitude': safe_float(get_field('LAUNCH_LONGITUDE')),
    }
    
    ds.close()
    
    # Upsert metadata
    await conn.execute("""
        INSERT INTO float_metadata (
            platform_number, float_serial_number, pi_name, project_name,
            deployment_platform, firmware_version, float_owner, operating_institute,
            launch_date, start_date, end_of_life, launch_latitude, launch_longitude
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (platform_number) DO UPDATE SET
            float_serial_number = COALESCE(EXCLUDED.float_serial_number, float_metadata.float_serial_number),
            pi_name = COALESCE(EXCLUDED.pi_name, float_metadata.pi_name),
            project_name = COALESCE(EXCLUDED.project_name, float_metadata.project_name),
            deployment_platform = COALESCE(EXCLUDED.deployment_platform, float_metadata.deployment_platform),
            firmware_version = COALESCE(EXCLUDED.firmware_version, float_metadata.firmware_version),
            float_owner = COALESCE(EXCLUDED.float_owner, float_metadata.float_owner),
            operating_institute = COALESCE(EXCLUDED.operating_institute, float_metadata.operating_institute),
            launch_date = COALESCE(EXCLUDED.launch_date, float_metadata.launch_date),
            start_date = COALESCE(EXCLUDED.start_date, float_metadata.start_date),
            end_of_life = COALESCE(EXCLUDED.end_of_life, float_metadata.end_of_life),
            launch_latitude = COALESCE(EXCLUDED.launch_latitude, float_metadata.launch_latitude),
            launch_longitude = COALESCE(EXCLUDED.launch_longitude, float_metadata.launch_longitude)
    """, metadata['platform_number'], metadata['float_serial_number'], 
        metadata['pi_name'], metadata['project_name'], metadata['deployment_platform'],
        metadata['firmware_version'], metadata['float_owner'], metadata['operating_institute'],
        metadata['launch_date'], metadata['start_date'], metadata['end_of_life'],
        metadata['launch_latitude'], metadata['launch_longitude'])
    
    logger.info(f"Metadata updated for float {platform_number}")
    return platform_number

async def ingest_profiles(prof_file: str, conn) -> tuple:
    """Ingest profiles from *_prof.nc file"""
    ds = xr.open_dataset(prof_file)
    
    platform_number = int(safe_str(ds.PLATFORM_NUMBER.values[0]))
    n_profs = ds.dims['N_PROF']
    
    total_measurements = 0
    
    for i in range(n_profs):
        cycle_number = int(ds.CYCLE_NUMBER.values[i])
        profile_date = safe_date(ds.JULD.values[i]) or datetime.now()
        lat = safe_float(ds.LATITUDE.values[i])
        lon = safe_float(ds.LONGITUDE.values[i])
        
        # Upsert profile
        await conn.execute("""
            INSERT INTO profiles (float_id, cycle_number, profile_date, latitude, longitude)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (float_id, cycle_number) DO NOTHING
        """, platform_number, cycle_number, profile_date, lat, lon)
        
        # Insert measurements
        pres = ds.PRES.values[i]
        temp = ds.TEMP.values[i]
        psal = ds.PSAL.values[i]
        
        records = []
        for lvl in range(len(pres)):
            p_val = float(pres[lvl])
            if np.isnan(p_val): continue
            
            t_val = safe_float(temp[lvl])
            s_val = safe_float(psal[lvl])
            
            if t_val is None and s_val is None: continue
            
            records.append((platform_number, cycle_number, int(lvl), p_val, p_val, t_val, s_val))
        
        if records:
            await conn.copy_records_to_table(
                'measurements', records=records,
                columns=['float_id', 'cycle_number', 'n_level', 'pressure', 'depth_m', 'temperature', 'salinity'],
                schema_name='public'
            )
            total_measurements += len(records)
    
    ds.close()
    logger.info(f"Ingested {n_profs} profiles, {total_measurements} measurements for float {platform_number}")
    return (n_profs, total_measurements)

async def ingest_float(float_id: str, db_url: str, data_dir: str = DATA_DIR) -> Dict[str, Any]:
    """
    Ingest both metadata and profiles for a float
    
    Returns:
        {
            "success": bool,
            "float_id": str,
            "profiles_count": int,
            "measurements_count": int,
            "message": str,
            "error": str (if failed)
        }
    """
    meta_file = os.path.join(data_dir, f"{float_id}_meta.nc")
    prof_file = os.path.join(data_dir, f"{float_id}_prof.nc")
    
    # Check if files exist
    if not os.path.exists(meta_file) and not os.path.exists(prof_file):
        return {
            "success": False,
            "float_id": float_id,
            "error": "Files not found",
            "message": f"NetCDF files not found for float {float_id}. Download first."
        }
    
    try:
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        
        profiles_count = 0
        measurements_count = 0
        
        try:
            if os.path.exists(meta_file):
                await ingest_metadata(meta_file, conn)
            
            if os.path.exists(prof_file):
                profiles_count, measurements_count = await ingest_profiles(prof_file, conn)
        finally:
            await conn.close()
        
        return {
            "success": True,
            "float_id": float_id,
            "profiles_count": profiles_count,
            "measurements_count": measurements_count,
            "message": f"Ingested float {float_id}: {profiles_count} profiles, {measurements_count} measurements"
        }
        
    except Exception as e:
        logger.error(f"Ingestion failed for float {float_id}: {e}")
        return {
            "success": False,
            "float_id": float_id,
            "error": str(e),
            "message": f"Ingestion failed: {str(e)}"
        }
