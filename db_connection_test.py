import asyncio
import asyncpg
import logging
import socket
import dns.resolver
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection details from backend12.py
DB_URL = "postgresql://postgres.locaacxacuphdlfautru:nawal12345@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

async def test_dns(host):
    """Test DNS resolution"""
    logger.info(f"Testing DNS resolution for {host}")
    try:
        # Try basic socket resolution
        ip = socket.gethostbyname(host)
        logger.info(f"Basic DNS resolution successful: {ip}")
        
        # Try detailed DNS lookup
        answers = dns.resolver.resolve(host, 'A')
        logger.info(f"DNS records found:")
        for rdata in answers:
            logger.info(f"  IP: {rdata}")
        return True
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed: {e}")
        return False
    except Exception as e:
        logger.error(f"DNS lookup error: {e}")
        return False

async def test_tcp_connection(host, port):
    """Test raw TCP connection"""
    logger.info(f"Testing TCP connection to {host}:{port}")
    try:
        reader, writer = await asyncio.open_connection(host, port)
        logger.info("TCP connection successful")
        writer.close()
        await writer.wait_closed()
        return True
    except Exception as e:
        logger.error(f"TCP connection failed: {e}")
        return False

async def test_db_connection():
    """Test full database connection"""
    logger.info("Testing database connection")
    try:
        # Parse connection URL
        parsed = urlparse(DB_URL)
        host = parsed.hostname
        port = parsed.port or 5432
        
        # Step 1: DNS Resolution
        dns_ok = await test_dns(host)
        if not dns_ok:
            logger.error("DNS resolution failed - cannot proceed with connection test")
            return False
        
        # Step 2: TCP Connection
        tcp_ok = await test_tcp_connection(host, port)
        if not tcp_ok:
            logger.error("TCP connection failed - cannot proceed with database connection")
            return False
        
        # Step 3: Full Database Connection
        logger.info("Attempting full database connection")
        conn = await asyncpg.connect(DB_URL)
        
        # Test query
        version = await conn.fetchval('SELECT version()')
        logger.info(f"Database connection successful!")
        logger.info(f"PostgreSQL version: {version}")
        
        # Test schema access
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            LIMIT 5
        """)
        logger.info("Available tables:")
        for table in tables:
            logger.info(f"  {table['table_name']}")
        
        await conn.close()
        return True
        
    except asyncpg.InvalidCatalogNameError:
        logger.error("Database does not exist")
        return False
    except asyncpg.InvalidPasswordError:
        logger.error("Invalid password")
        return False
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        return False

async def main():
    """Run all connection tests"""
    logger.info("Starting database connection tests...")
    logger.info(f"Using database URL: {DB_URL}")
    
    success = await test_db_connection()
    
    if success:
        logger.info("All connection tests passed!")
    else:
        logger.error("Connection testing failed - check logs above for details")

if __name__ == "__main__":
    asyncio.run(main())