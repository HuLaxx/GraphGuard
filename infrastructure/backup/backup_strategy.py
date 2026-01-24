"""
GraphGuard - Backup Configuration
==================================
File: infrastructure/backup/backup_strategy.py

Automated backup management for PostgreSQL, Neo4j, Redis, and model artifacts.
Designed to run as a Kubernetes CronJob or standalone script.
"""

import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import boto3
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Configuration
# ============================================

class BackupConfig:
    """Backup configuration from environment."""
    
    # S3 Settings
    S3_BUCKET = os.getenv('BACKUP_S3_BUCKET', 'graphguard-backups')
    S3_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Retention
    RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    
    # PostgreSQL
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'graphguard')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'graphguard')
    
    # Neo4j
    NEO4J_HOST = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    
    # Local backup directory
    LOCAL_BACKUP_DIR = Path(os.getenv('BACKUP_LOCAL_DIR', '/tmp/backups'))


# ============================================
# S3 Client
# ============================================

def get_s3_client():
    """Get configured S3 client."""
    return boto3.client('s3', region_name=BackupConfig.S3_REGION)


def upload_to_s3(local_path: Path, s3_key: str) -> bool:
    """Upload file to S3."""
    try:
        s3 = get_s3_client()
        s3.upload_file(str(local_path), BackupConfig.S3_BUCKET, s3_key)
        logger.info("Uploaded to S3", bucket=BackupConfig.S3_BUCKET, key=s3_key)
        return True
    except Exception as e:
        logger.error("S3 upload failed", error=str(e))
        return False


def cleanup_old_backups(prefix: str, retention_days: int = None):
    """Delete S3 objects older than retention period."""
    retention_days = retention_days or BackupConfig.RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    try:
        s3 = get_s3_client()
        paginator = s3.get_paginator('list_objects_v2')
        
        deleted_count = 0
        for page in paginator.paginate(Bucket=BackupConfig.S3_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    s3.delete_object(Bucket=BackupConfig.S3_BUCKET, Key=obj['Key'])
                    deleted_count += 1
        
        logger.info("Cleaned up old backups", prefix=prefix, deleted=deleted_count)
    except Exception as e:
        logger.error("Backup cleanup failed", error=str(e))


# ============================================
# PostgreSQL Backup
# ============================================

def backup_postgresql() -> Optional[Path]:
    """
    Create PostgreSQL backup using pg_dump.
    Returns path to compressed backup file.
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_name = f"postgres_{BackupConfig.POSTGRES_DB}_{timestamp}.sql.gz"
    backup_path = BackupConfig.LOCAL_BACKUP_DIR / backup_name
    
    BackupConfig.LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    env['PGPASSWORD'] = BackupConfig.POSTGRES_PASSWORD
    
    try:
        # Run pg_dump
        cmd = [
            'pg_dump',
            '-h', BackupConfig.POSTGRES_HOST,
            '-p', BackupConfig.POSTGRES_PORT,
            '-U', BackupConfig.POSTGRES_USER,
            '-d', BackupConfig.POSTGRES_DB,
            '-Fc',  # Custom format for faster restore
        ]
        
        with gzip.open(backup_path, 'wb') as f:
            result = subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            f.write(result.stdout)
        
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info("PostgreSQL backup created", path=str(backup_path), size_mb=f"{size_mb:.2f}")
        
        return backup_path
    
    except subprocess.CalledProcessError as e:
        logger.error("PostgreSQL backup failed", error=e.stderr.decode())
        return None
    except Exception as e:
        logger.error("PostgreSQL backup failed", error=str(e))
        return None


# ============================================
# Neo4j Backup
# ============================================

def backup_neo4j() -> Optional[Path]:
    """
    Create Neo4j backup using neo4j-admin.
    Note: Requires Neo4j Enterprise for online backup.
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_dir = BackupConfig.LOCAL_BACKUP_DIR / f"neo4j_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # For Neo4j Enterprise with online backup
        cmd = [
            'neo4j-admin', 'database', 'backup',
            '--from', BackupConfig.NEO4J_HOST.replace('bolt://', ''),
            '--to-path', str(backup_dir),
            '--database', 'neo4j'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback: export using Cypher (works with Community Edition)
            return backup_neo4j_cypher_export(backup_dir)
        
        # Compress backup
        archive_path = BackupConfig.LOCAL_BACKUP_DIR / f"neo4j_{timestamp}.tar.gz"
        shutil.make_archive(
            str(archive_path).replace('.tar.gz', ''),
            'gztar',
            backup_dir.parent,
            backup_dir.name
        )
        
        # Cleanup uncompressed
        shutil.rmtree(backup_dir)
        
        logger.info("Neo4j backup created", path=str(archive_path))
        return archive_path
    
    except Exception as e:
        logger.error("Neo4j backup failed", error=str(e))
        return None


def backup_neo4j_cypher_export(backup_dir: Path) -> Optional[Path]:
    """
    Fallback: Export Neo4j data using Cypher queries.
    Works with Community Edition.
    """
    from neo4j import GraphDatabase
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    export_file = BackupConfig.LOCAL_BACKUP_DIR / f"neo4j_export_{timestamp}.cypher"
    
    try:
        driver = GraphDatabase.driver(
            BackupConfig.NEO4J_HOST,
            auth=(BackupConfig.NEO4J_USER, BackupConfig.NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            # Export nodes and relationships as Cypher statements
            with open(export_file, 'w') as f:
                # Export nodes
                result = session.run("MATCH (n) RETURN n")
                for record in result:
                    node = record['n']
                    labels = ':'.join(node.labels)
                    props = dict(node)
                    f.write(f"CREATE (:{labels} {props});\n")
                
                # Export relationships
                result = session.run("MATCH ()-[r]->() RETURN r")
                for record in result:
                    rel = record['r']
                    f.write(f"// Relationship: {rel.type}\n")
        
        driver.close()
        
        # Compress
        with open(export_file, 'rb') as f_in:
            with gzip.open(f"{export_file}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        export_file.unlink()
        compressed_path = Path(f"{export_file}.gz")
        
        logger.info("Neo4j Cypher export created", path=str(compressed_path))
        return compressed_path
    
    except Exception as e:
        logger.error("Neo4j Cypher export failed", error=str(e))
        return None


# ============================================
# Redis Backup
# ============================================

def backup_redis() -> Optional[Path]:
    """
    Create Redis backup using BGSAVE.
    """
    import redis
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    try:
        r = redis.Redis(
            host=BackupConfig.REDIS_HOST,
            port=BackupConfig.REDIS_PORT,
            password=BackupConfig.REDIS_PASSWORD or None
        )
        
        # Trigger background save
        r.bgsave()
        
        # Wait for save to complete
        while r.lastsave() == r.lastsave():
            import time
            time.sleep(1)
        
        # Note: Actual RDB file is on Redis server
        # For ElastiCache, use snapshot feature instead
        logger.info("Redis BGSAVE triggered")
        
        # Export key summary (metadata)
        backup_path = BackupConfig.LOCAL_BACKUP_DIR / f"redis_keys_{timestamp}.txt"
        BackupConfig.LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(backup_path, 'w') as f:
            info = r.info()
            f.write(f"# Redis Backup Metadata\n")
            f.write(f"# Timestamp: {timestamp}\n")
            f.write(f"# Total Keys: {info.get('db0', {}).get('keys', 0)}\n")
            f.write(f"# Memory Used: {info.get('used_memory_human', 'N/A')}\n")
        
        return backup_path
    
    except Exception as e:
        logger.error("Redis backup failed", error=str(e))
        return None


# ============================================
# ML Model Backup
# ============================================

def backup_models() -> bool:
    """
    Backup ML model artifacts to S3.
    """
    model_paths = [
        Path('models/xgboost_rigorous/xgboost_fraud.json'),
        Path('models/gat/gat_fraud.pth'),
    ]
    
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    success = True
    
    for model_path in model_paths:
        if model_path.exists():
            s3_key = f"models/{timestamp}/{model_path.name}"
            if not upload_to_s3(model_path, s3_key):
                success = False
        else:
            logger.warning("Model not found", path=str(model_path))
    
    return success


# ============================================
# Full Backup Job
# ============================================

def run_full_backup():
    """
    Run complete backup of all systems.
    Designed to be called from CronJob.
    """
    logger.info("Starting full backup job")
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    results = {}
    
    # PostgreSQL
    pg_backup = backup_postgresql()
    if pg_backup:
        upload_to_s3(pg_backup, f"postgres/{timestamp}/{pg_backup.name}")
        pg_backup.unlink()
        results['postgresql'] = 'success'
    else:
        results['postgresql'] = 'failed'
    
    # Neo4j
    neo_backup = backup_neo4j()
    if neo_backup:
        upload_to_s3(neo_backup, f"neo4j/{timestamp}/{neo_backup.name}")
        neo_backup.unlink()
        results['neo4j'] = 'success'
    else:
        results['neo4j'] = 'failed'
    
    # Redis (metadata only, actual backup via ElastiCache)
    redis_backup = backup_redis()
    if redis_backup:
        upload_to_s3(redis_backup, f"redis/{timestamp}/{redis_backup.name}")
        redis_backup.unlink()
        results['redis'] = 'success'
    else:
        results['redis'] = 'skipped'
    
    # ML Models
    if backup_models():
        results['models'] = 'success'
    else:
        results['models'] = 'failed'
    
    # Cleanup old backups
    cleanup_old_backups('postgres/')
    cleanup_old_backups('neo4j/')
    cleanup_old_backups('redis/')
    
    logger.info("Backup job completed", results=results)
    return results


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GraphGuard Backup Manager")
    parser.add_argument(
        'action',
        choices=['full', 'postgres', 'neo4j', 'redis', 'models', 'cleanup'],
        help='Backup action to perform'
    )
    args = parser.parse_args()
    
    if args.action == 'full':
        run_full_backup()
    elif args.action == 'postgres':
        backup_postgresql()
    elif args.action == 'neo4j':
        backup_neo4j()
    elif args.action == 'redis':
        backup_redis()
    elif args.action == 'models':
        backup_models()
    elif args.action == 'cleanup':
        cleanup_old_backups('postgres/')
        cleanup_old_backups('neo4j/')
