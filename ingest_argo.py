import os
import glob
import asyncio
import asyncpg
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration (Align with backend16.py)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ArgoIngester:
    def __init__(self, db_url):
        self.db_url = db_url

    async def ingest_file(self, file_path: str):
        """Ingest a single ARGO NetCDF file"""
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Open NetCDF file
            ds = xr.open_dataset(file_path)
            
            # Extract Metadata (handle both bytes and strings)
            def safe_str(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8').strip()
                return str(val).strip()
            
            platform_number = int(safe_str(ds.PLATFORM_NUMBER.values[0]))
            pi_name = safe_str(ds.PI_NAME.values[0])
            project_name = safe_str(ds.PROJECT_NAME.values[0])
            
            logger.info(f"Float ID: {platform_number}, PI: {pi_name}")

            # Connect to DB (disable statement cache for Supabase compatibility)
            conn = await asyncpg.connect(self.db_url, statement_cache_size=0)
            try:
                # 1. Upsert Float Metadata
                await conn.execute("""
                    INSERT INTO float_metadata (
                        platform_number, pi_name, project_name, float_owner, 
                        operating_institute, deployment_platform
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (platform_number) DO UPDATE SET
                        pi_name = EXCLUDED.pi_name,
                        project_name = EXCLUDED.project_name
                """, platform_number, pi_name, project_name, "Unknown", "Unknown", "Unknown")
                
                # 2. Extract Profiles & Measurements
                # Argo data is (N_PROF, N_LEVELS)
                n_profs = ds.dims['N_PROF']
                
                for i in range(n_profs):
                    cycle_number = int(ds.CYCLE_NUMBER.values[i])
                    date_val = ds.JULD.values[i]
                    profile_date = pd.to_datetime(date_val).to_pydatetime() if pd.notnull(date_val) else datetime.now()
                    lat = float(ds.LATITUDE.values[i]) if pd.notnull(ds.LATITUDE.values[i]) else None
                    lon = float(ds.LONGITUDE.values[i]) if pd.notnull(ds.LONGITUDE.values[i]) else None
                    
                    # Insert Profile
                    await conn.execute("""
                        INSERT INTO profiles (
                            float_id, cycle_number, profile_date, latitude, longitude
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (float_id, cycle_number) DO NOTHING
                    """, platform_number, cycle_number, profile_date, lat, lon)
                    
                    # Extract Measurements (Temp, Psal, Pres)
                    pres = ds.PRES.values[i]
                    temp = ds.TEMP.values[i]
                    psal = ds.PSAL.values[i]
                    
                    # Write measurements in batches
                    records = []
                    for lvl in range(len(pres)):
                        p_val = float(pres[lvl])
                        if np.isnan(p_val): continue
                        
                        t_val = float(temp[lvl]) if not np.isnan(temp[lvl]) else None
                        s_val = float(psal[lvl]) if not np.isnan(psal[lvl]) else None
                        
                        if t_val is None and s_val is None: continue
                        
                        records.append((
                            platform_number, cycle_number, int(lvl),
                            p_val, p_val, # depth_m approximation
                            t_val, s_val
                        ))
                    
                    if records:
                        await conn.copy_records_to_table(
                            'measurements',
                            records=records,
                            columns=['float_id', 'cycle_number', 'n_level', 'pressure', 'depth_m', 'temperature', 'salinity'],
                            schema_name='public'
                        )
                        logger.info(f"Inserted {len(records)} measurements for cycle {cycle_number}")

            finally:
                await conn.close()
                ds.close()
                
            logger.info(f"Successfully ingested {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")
            return False

    async def ingest_directory(self, directory: str):
        """Ingest all .nc files in a directory"""
        files = glob.glob(os.path.join(directory, "*.nc"))
        logger.info(f"Found {len(files)} NetCDF files in {directory}")
        
        for f in files:
            await self.ingest_file(f)

if __name__ == "__main__":
    # Example Usage
    async def main():
        ingester = ArgoIngester(DATABASE_URL)
        
        # User: Put your NetCDF files in a folder named 'netcdf_data'
        data_dir = "netcdf_data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"Created {data_dir}. Please place your .nc files there.")
        else:
            await ingester.ingest_directory(data_dir)
            
    asyncio.run(main())
